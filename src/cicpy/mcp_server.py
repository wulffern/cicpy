#!/usr/bin/env python3
"""MCP server exposing cicpy's layout inspection as tools.

Lets an agent doing schematic driven layout render a cell (returned as an
inline image, flipped so y is up like the layout), inspect the placement
of a cic file, query a spice netlist for connectivity, run the design
repo's own DRC target, and read the layout field guide.

cicpy is technology independent, and so is this server: the technology
file is always an argument, and DRC runs through the design repository's
own `make drc` so the rules and tools stay where the repository put them.

Run directly:

    cicpy-mcp

Or point an MCP client's config at the `cicpy-mcp` console script.
Requires `pip install cicpy[mcp]` for the server framework.
"""

import collections
import glob
import json
import os
import re
import subprocess
import tempfile

#- The MCP Python SDK renamed FastMCP to MCPServer in 2.0 and moved it out of
#- mcp.server.fastmcp. The constructor kwargs, the .tool() decorator, .run()
#- and Image are otherwise source-compatible, so accept either generation
#- rather than pinning users to one.
try:
    from mcp.server.mcpserver import Image, MCPServer as _Server  # SDK >= 2.0
except ImportError:  # pragma: no cover - depends on the installed SDK
    from mcp.server.fastmcp import FastMCP as _Server, Image  # SDK 1.x

mcp = _Server(
    "cicpy",
    instructions=(
        "Tools for schematic driven layout with cicpy. 'render' draws a "
        "cell from a cic file and returns the image inline, y up. "
        "'cell_info' reports placement: instances, groups, pitches and "
        "ports. 'netlist_info' reports which devices connect to which "
        "nets, read it before choosing placement groups. 'drc' runs the "
        "design repository's own make drc and reports the rules that "
        "fired. 'layout_guide' returns the field guide, read it first."
    ),
)


def _load_cells(cicfile):
    with open(cicfile) as fi:
        design = json.load(fi)
    return [c for c in design.get("cells", []) if isinstance(c, dict)]


def _group_of(name):
    m = re.match(r"(x\D+)", name or "")
    return m.group(1) if m else ""


@mcp.tool()
def layout_guide() -> str:
    """Return the cicpy layout field guide.

    The guide covers the work loop (generate, drc, render, adjust), the
    placement API in usage order, the spacing values known to be DRC
    clean, the geometry model (abutment boxes, overlap tiling, routing
    channels) and the route language. Read it before doing layout.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(here, "data", "agent_layout.md"),
        os.path.join(here, "..", "..", "docs", "agent_layout.md"),
    ):
        if os.path.isfile(candidate):
            with open(candidate) as fi:
                return fi.read()
    return (
        "agent_layout.md not found in this install. The guide lives at "
        "https://analogicus.com/cicpy/agent_layout in rendered form."
    )


@mcp.tool()
def cell_info(cicfile: str, cell: str | None = None) -> str:
    """Report the placement stored in a cic file.

    Without `cell`, lists the cells in the file. With a cell name:
    the abutment box, every instance with position and orientation,
    per group extents and vertical pitches, and every port with its
    geometry. A port without geometry is reported loudly, it means
    the generator lost it.

    Args:
        cicfile: Path to the .cic file.
        cell: Cell name to inspect. Omit to list cells.
    """
    cells = _load_cells(cicfile)
    if cell is None:
        names = [c.get("name", "?") for c in cells]
        return f"{len(names)} cells:\n" + "\n".join(names)

    target = next((c for c in cells if c.get("name") == cell), None)
    if target is None:
        return f"no cell named {cell!r} in {cicfile}"

    out = [f"cell {cell}"]
    box = [target.get(k) for k in ("x1", "y1", "x2", "y2")]
    if all(v is not None for v in box):
        out.append(f"abutment box {box[0]} {box[1]} {box[2]} {box[3]}")

    groups = collections.defaultdict(list)
    ports = []
    for ch in target.get("children", []):
        if not isinstance(ch, dict):
            continue
        cls = str(ch.get("class", ""))
        if "Instance" in cls:
            iname = ch.get("instanceName") or ch.get("name") or ""
            groups[_group_of(iname)].append(ch)
        elif "Port" in cls:
            ports.append(ch)

    for g, insts in sorted(groups.items()):
        xs = sorted({int(i.get("x1", 0)) for i in insts})
        ys = sorted(int(i.get("y1", 0)) for i in insts)
        pitches = sorted({ys[i + 1] - ys[i] for i in range(len(ys) - 1)})
        cellnames = sorted({str(i.get("cell", i.get("name", "?"))) for i in insts})
        out.append(
            f"group {g or '?'}: n={len(insts)} x={xs} "
            f"y={ys[0]}..{ys[-1]} pitches={pitches} cells={cellnames}"
        )
        for i in insts:
            angle = i.get("angle") or "R0"
            iname = i.get("instanceName") or i.get("name") or "?"
            out.append(
                f"  {iname:24s} {str(i.get('cell', '')):28s} "
                f"({i.get('x1')},{i.get('y1')}) {angle}"
            )

    for p in ports:
        x1, y1, x2, y2 = (p.get(k) for k in ("x1", "y1", "x2", "y2"))
        broken = x1 == x2 or y1 == y2
        flag = "  <-- NO GEOMETRY, broken" if broken else ""
        out.append(
            f"port {p.get('name'):8s} {str(p.get('layer', '')):4s} "
            f"({x1},{y1})..({x2},{y2}){flag}"
        )

    return "\n".join(out)


@mcp.tool()
def netlist_info(spicefile: str, subckt: str) -> str:
    """Report the connectivity of a spice subcircuit.

    For every net: the devices on it and which terminal they connect
    with. This is what placement groups must follow, read it before
    grouping and renaming instances.

    Args:
        spicefile: Path to the spice netlist.
        subckt: Subcircuit name to inspect.
    """
    lines = []
    with open(spicefile) as fi:
        for raw in fi:
            raw = raw.rstrip("\n")
            if raw.strip().startswith("+") and lines:
                lines[-1] += " " + raw.strip().lstrip("+")
            else:
                lines.append(raw)

    body = []
    header = None
    in_ckt = False
    for l in lines:
        m = re.match(r"\s*\.subckt\s+(\S+)\s*(.*)", l, re.I)
        if m:
            if m.group(1).lower() == subckt.lower():
                in_ckt = True
                header = m.group(2).split()
            continue
        if re.match(r"\s*\.ends", l, re.I):
            if in_ckt:
                break
            continue
        if in_ckt and l.strip() and not l.strip().startswith("*"):
            body.append(l.strip())

    if header is None:
        return f"no subckt {subckt!r} in {spicefile}"

    nets = collections.defaultdict(list)
    devices = []
    for l in body:
        tok = l.split()
        if not tok:
            continue
        inst = tok[0]
        #- terminals are everything between the instance name and the
        #- referenced cell; parameters carry '='
        rest = [t for t in tok[1:] if "=" not in t]
        if len(rest) < 2:
            continue
        cellname = rest[-1]
        terms = rest[:-1]
        devices.append(f"{inst} -> {cellname} ({' '.join(terms)})")
        for idx, net in enumerate(terms):
            nets[net].append(f"{inst}.{idx}")

    out = [f"subckt {subckt} ports: {' '.join(header)}", f"{len(devices)} devices:"]
    out += ["  " + d for d in devices]
    out.append("nets:")
    for net, users in sorted(nets.items()):
        out.append(f"  {net:16s} {' '.join(users)}")
    return "\n".join(out)


@mcp.tool()
def render(
    cicfile: str,
    techfile: str,
    library: str,
    cell: str | None = None,
    includes: list[str] | None = None,
    height: int = 1200,
) -> Image:
    """Render a cell to an image and return it inline.

    The image is flipped so y points up, matching layout coordinates:
    the row you placed on top is at the top of the picture.

    Args:
        cicfile: Path to the .cic file.
        techfile: Path to the technology file (always an argument,
            cicpy carries no technology of its own).
        library: Library name, used for the output naming.
        cell: Cell to render. Omit to render the last cell in the file,
            which is usually the top.
        includes: Other .cic files the design references (--I).
        height: Raster height in pixels.
    """
    from . import cic as ciclib

    cells = _load_cells(cicfile)
    if cell is None:
        cell = cells[-1].get("name") if cells else None
    if cell is None:
        raise ValueError(f"no cells in {cicfile}")

    cicfile = os.path.abspath(cicfile)
    techfile = os.path.abspath(techfile)
    includes = [os.path.abspath(i) for i in (includes or [])]

    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(prefix="cicpy_mcp_")
    try:
        os.chdir(tmpdir)
        rules = ciclib.Rules(techfile)
        design = ciclib.Design()
        design.fromJsonFilesWithDependencies(cicfile, includes)
        printer = ciclib.SvgPrinter(library, rules, 10, 100, 100)
        printer.print(design)
        matches = glob.glob(os.path.join(tmpdir, "*_svg", cell + ".svg"))
        if not matches:
            raise ValueError(f"no svg produced for cell {cell!r}")
        svgfile = matches[0]
        pngfile = os.path.join(tmpdir, cell + ".png")
        try:
            import cairosvg

            cairosvg.svg2png(url=svgfile, write_to=pngfile,
                             output_height=height, background_color="white")
        except ImportError:
            subprocess.run(
                ["rsvg-convert", "-h", str(height), "-b", "white",
                 svgfile, "-o", pngfile],
                check=True,
            )
        try:
            from PIL import Image as PILImage

            with PILImage.open(pngfile) as im:
                im.transpose(PILImage.FLIP_TOP_BOTTOM).save(pngfile)
        except ImportError:
            #- without PIL the image stays y down; the guide warns about it
            pass
        with open(pngfile, "rb") as fh:
            data = fh.read()
    finally:
        os.chdir(cwd)
    return Image(data=data, format="png")


@mcp.tool()
def drc(workdir: str, cell: str) -> str:
    """Run the design repository's own DRC and report what fired.

    Runs `make drc CELL=<cell>` in `workdir`, which is the contract
    every design repository maintains; the technology and the tools
    stay in the repository, cicpy adds none of its own. Returns the
    rule messages and the error count from the DRC log.

    Args:
        workdir: The repository's work directory, where make runs.
        cell: The cell to check.
    """
    proc = subprocess.run(
        ["make", "drc", f"CELL={cell}"],
        cwd=workdir, capture_output=True, text=True,
    )
    log = os.path.join(workdir, "drc", f"{cell}_drc.log")
    if not os.path.isfile(log):
        return (
            f"make drc exited {proc.returncode} and no {log} was written.\n"
            f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
        )

    noise = re.compile(
        r"^(Cell |Loading|Input|Scaled|The follow|\s+ubm|Processing"
        r"|Timestamp|DRC style|Usage|Coordinate|Sourcing|logcommands"
        r"|WARNING|Warning|Using|Starting|Magic |\d+ Magic|/|\s"
        r"|Load |No errors|$)"
    )
    rules = []
    count = "?"
    with open(log) as fi:
        for l in fi:
            l = l.rstrip("\n")
            m = re.match(r"Total DRC errors found: (\d+)", l)
            if m:
                count = m.group(1)
                continue
            if not noise.match(l):
                rules.append(l)

    out = [f"{cell}: {count} DRC errors"]
    if rules:
        out.append("rules:")
        out += ["  " + r for r in dict.fromkeys(rules)]
    if count not in ("?", "0"):
        out.append(
            "for coordinates, step the errors in magic with drc find, "
            "see the layout guide"
        )
    return "\n".join(out)


def _parse_connectivity(log_text):
    shorts, opens = [], []
    for l in log_text.split("\n"):
        m = re.search(r"WARNING: (?:ROUTE )?SHORT (component=\S+ nets=\S+.*)", l)
        if m and "ROUTE SHORT" not in l:
            shorts.append(re.sub(r"\x1b\[[0-9;]*m", "", m.group(1)))
        m = re.search(r"WARNING: OPEN (net=\S+ split_components=[^\x1b]+)", l)
        if m:
            opens.append(re.sub(r"\x1b\[[0-9;]*m", "", m.group(1)))
    return shorts, opens


@mcp.tool()
def connectivity(workdir: str, library: str, cell: str) -> str:
    """Check layout connectivity: shorts and opens, with route attribution.

    Reruns the design repository's sch2mag flow with the connectivity
    check enabled, which is the same analysis the layout GUI shows. A
    SHORT lists the merged nets and, when a route caused it, the exact
    python route command and file:line that drew it. An OPEN lists a net
    whose pins are not all connected yet. Run this after every routing
    change, and do not add more routes on top of a reported short.

    Args:
        workdir: The repository's work directory, where make runs.
        library: The design library name.
        cell: The cell to check.
    """
    proc = subprocess.run(
        ["cicpy", "sch2mag", "--check-connectivity", library, cell],
        cwd=workdir, capture_output=True, text=True,
    )
    shorts, opens = _parse_connectivity(proc.stdout + proc.stderr)
    out = [f"{cell}: {len(shorts)} shorts, {len(opens)} opens"]
    if shorts:
        out.append("shorts:")
        out += ["  " + s for s in shorts]
    if opens:
        out.append("opens:")
        out += ["  " + o for o in opens]
    if not shorts and not opens:
        out.append("clean")
    if proc.returncode != 0:
        out.append(f"(sch2mag exited {proc.returncode})")
    return "\n".join(out)


@mcp.tool()
def checkroutes(cicfile: str, techfile: str, cell: str, includes: list[str] | None = None) -> str:
    """Check a cell in an existing .cic for shorts and opens.

    The same analysis as `connectivity`, but reading a .cic that is
    already on disk rather than re-running placement. Use this for a
    ciccreator library, where sch2mag would replace the layout instead
    of judging it, and for any case where the layout under test must not
    be touched.

    A leaf cell that carries no substrate tap reports its supply rails
    as split: that is the library design, not a defect, and the tap cell
    joins them at the assembly.

    Args:
        cicfile: Path to the .cic holding the layout.
        techfile: Path to the technology file.
        cell: The cell to check.
        includes: Other .cic files the design references.
    """
    cmd = ["cicpy", "checkroutes", cicfile, techfile, cell]
    for inc in (includes or []):
        cmd += ["--I", inc]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    shorts, opens = _parse_connectivity(proc.stdout + proc.stderr)
    out = [f"{cell}: {len(shorts)} shorts, {len(opens)} opens"]
    if shorts:
        out.append("shorts:")
        out += ["  " + s for s in shorts]
    if opens:
        out.append("opens:")
        out += ["  " + o for o in opens]
    if not shorts and not opens:
        out.append("clean")
    return "\n".join(out)


@mcp.tool()
def tracks(cicfile: str, techfile: str, cell: str, layer: str = "",
           band: str = "", free: str = "",
           includes: list[str] | None = None) -> str:
    """Which routing tracks are occupied, and by what.

    Read this *before* choosing a track number. A route is placed with a
    track that is an offset from the net's own pins, so two nets in the
    same column land on each other at the same number and neither can
    tell. Finding that out by drawing it and reading the short report
    costs a full regeneration per guess.

    Args:
        cicfile: Path to the .cic holding the layout.
        techfile: Path to the technology file.
        cell: The cell to inspect.
        layer: Restrict to one layer, e.g. "M3".
        band: "LO:HI", only tracks whose coordinate is in that range.
              A routing channel is a band.
        free: "LO:HI", report the tracks free *over that span* rather
              than the ones wholly empty. This is usually the real
              question: a track carrying a short wire at one end is
              still usable at the other.
        includes: Other .cic files the design references.
    """
    cmd = ["cicpy", "tracks", cicfile, techfile, cell]
    if layer:
        cmd += ["--layer", layer]
    if band:
        cmd += ["--band", band]
    if free:
        cmd += ["--free", free]
    for inc in (includes or []):
        cmd += ["--I", inc]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout + proc.stderr)
    return out.strip() or "(no output)"


#- What each route option means. The names are checked against the
#- parser at call time, so this cannot quietly drift from the code: an
#- option the parser gained and this table has not is reported as
#- undocumented rather than hidden.
ROUTE_OPTIONS = {
    "placement": {
        "track<n>": "Which track the trunk takes, counted from this "
                    "net's OWN pins. Relative, so two nets in one column "
                    "get the same place at the same number and neither "
                    "can tell. Use a named channel instead when they clash.",
        "branchtrack<n>": "Same idea for the horizontal branch. Collapses "
                          "several branches onto one bar, which is what a "
                          "diode connection wants.",
        "verticaltrack<n>": "track<n> for orthogonal routes, trunk only.",
        "horizontaltrack<n>": "branchtrack<n> for orthogonal routes, bar only.",
        "hchannel=NAME,htrack=<n>": "Put the horizontal bar on track n of "
                                    "a channel registered by addRoutingChannel. "
                                    "Absolute in effect, portable in form: the "
                                    "channel's coordinates come from the "
                                    "placement, so a resize or another "
                                    "technology still works.",
        "vchannel=NAME,vtrack=<n>": "The same for the trunk. Both may appear "
                                    "in one option string.",
        "left / right / center / balanced": "Which side of its pins the trunk "
                                            "goes. Two nets whose pins share "
                                            "rows need opposite sides or the "
                                            "outer one crosses the inner.",
        "bandy<n> / trunkx<n>": "Raw coordinates. The resolved form of "
                                "hchannel/vchannel. Never write these in a "
                                "design, they survive neither a resize nor a "
                                "change of technology.",
    },
    "attachment": {
        "onTopLeft / onTopRight": "Which end of the access geometry the trunk "
                                  "anchors to, left or right.",
        "onTopTop / onTopBottom": "The same vertically.",
        "onTopL / onTopR / onTopT / onTopB": "Older spellings of the above.",
    },
    "shape": {
        "straight": "No jog, for -|- which has no alignment of its own.",
        "strap": "A power strap rather than a signal route.",
        "leftdownleftup / leftupleftdown": "Which way the L turns.",
        "vertical": "Force the vertical form of a strap.",
        "novert": "Suppress the vertical segment.",
        "antenna": "Add the antenna diode hop, jumping a layer up and back.",
    },
    "offsets": {
        "offsetlow / offsethigh": "Shift the route half a wire, to clear the "
                                  "neighbouring track.",
        "offsetlowend / offsethighend": "The same at the far end only.",
        "startoffsetcutlow / startoffsetcuthigh": "Move the start cut, and the "
                                                  "rect it lands on, half a cut.",
        "endoffsetcutlow / endoffsetcuthigh": "The same at the end.",
    },
    "cuts": {
        "nostartcut / noendcut": "Do not place the cut at that end. Use when "
                                 "the pin is already on the route's layer.",
        "2cuts / 2vcuts": "Cut count, for current or for reliability.",
        "cutalignright": "Align cuts to the right edge instead of the left.",
        "fillhcut / fillvcut": "Fill the whole access with cuts.",
    },
    "avoidance": {
        "avoidblocks": "Route around blockages instead of through them.",
        "avoidkeepouts / blockkeepouts": "Respect keepout regions.",
        "avoidboundaries / blockboundaries": "Respect cell boundaries.",
        "keepout": "Mark this route's own area as a keepout for later routes.",
    },
    "trim": {
        "trimstartleft / trimstartright": "Cut the trunk back at the start.",
        "trimendleft / trimendright": "The same at the end. Use to stop a bar "
                                      "before it reaches another net's trunk.",
    },
    "misc": {
        "routeWidth=<rule>": "Take the wire width from another rule, e.g. a "
                             "capacitor's own width rather than the layer minimum.",
        "nolabel": "Do not place the net label.",
        "noSpace": "Do not add the spacing margin.",
    },
}


@mcp.tool()
def route_options(name: str = "") -> str:
    """What each routing option means, and which ones lie to you.

    Pass a name or a fragment to get just that one. With no argument,
    the whole table grouped by what the option does.

    Read this before guessing at an option string. The important
    distinction it draws is relative versus placed: `track<n>` is an
    offset from the net's own pins, so it cannot separate two nets that
    share a column, while `hchannel`/`vchannel` name a gap the placement
    registered and can. Use `tracks` to find out which channel track is
    free before choosing.

    Args:
        name: An option or fragment, e.g. "track" or "offsetlow".
    """
    import cicpy.core.route as _route
    parsed = set()
    src = open(_route.__file__).read()
    for m in re.finditer(r'_option_int\(\s*(?:self\.)?options\s*,\s*"([a-zA-Z]+)"', src):
        parsed.add(m.group(1))
    for m in re.finditer(r're\.search\(\s*r?"([^"]+)"\s*,\s*(?:self\.)?options', src):
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", m.group(1)):
            if w not in ("s", "d", "w"):
                parsed.add(w)

    out = []
    documented = set()
    for group, entries in ROUTE_OPTIONS.items():
        rows = []
        for key, meaning in entries.items():
            for part in re.findall(r"[a-zA-Z][a-zA-Z0-9]*", key):
                documented.add(part)
            if name and name.lower() not in key.lower() and \
                    name.lower() not in meaning.lower():
                continue
            rows.append(f"  {key}\n      {meaning}")
        if rows:
            out.append(group + ":")
            out.extend(rows)

    if not name:
        missing = sorted(o for o in parsed if o not in documented)
        if missing:
            out.append("")
            out.append("parsed by route.py but not described above: "
                       + ", ".join(missing))
    if not out:
        return f"no route option matching {name!r}"
    return "\n".join(out)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
