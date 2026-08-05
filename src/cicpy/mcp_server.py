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


def main():
    mcp.run()


if __name__ == "__main__":
    main()
