#!/usr/bin/env python3
"""MCP server exposing cicpy's layout inspection as tools.

Lets an agent doing schematic driven layout render a cell or a finished
GDS (returned as an inline image, y up like the layout), inspect the
placement
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
import logging
import tempfile

#- The MCP Python SDK renamed FastMCP to MCPServer in 2.0 and moved it out of
#- mcp.server.fastmcp. The constructor kwargs, the .tool() decorator, .run()
#- and Image are otherwise source-compatible, so accept either generation
#- rather than pinning users to one.
try:
    from mcp.server.mcpserver import Image, MCPServer as _Server  # SDK >= 2.0
except ImportError:  # pragma: no cover - depends on the installed SDK
    from mcp.server.fastmcp import FastMCP as _Server, Image  # SDK 1.x


log = logging.getLogger("cicpy.mcp")

mcp = _Server(
    "cicpy",
    instructions=(
        "Tools for schematic driven layout with cicpy. 'render' draws a "
        "cell from a cic file and returns the image inline, y up; "
        "'render_gds' draws a finished GDS the same way, with "
        "'top_only' for a routing view that leaves the placed "
        "blocks as outlines. "
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


def _strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _run_cic(*args, includes=None):
    """Run a `cicpy` subcommand and return its de-colored output.

    THE one shell-out: command build, --I include forwarding, ANSI
    stripping and the empty-output fallback used to be copy-pasted
    per tool.
    """
    cmd = ["cicpy", *args]
    for inc in (includes or []):
        cmd += ["--I", inc]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = _strip_ansi(proc.stdout + proc.stderr)
    return out.strip() or "(no output)"


def _group_of(name):
    #- the ONE prefix rule (ciccreator's), shared with the router. The
    #- private regex here used r"(x\D+)", and \D matches '<': a bus
    #- instance xa<0> grouped as "xa<" and every bit became its own
    #- group in cell_info.
    from cicpy.core.mazerouter import stack_of
    return stack_of(name or "")


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
    flightlines: list[str] | None = None,
    auto_libs: bool = True,
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
        auto_libs: Find the design's other .cic libraries by itself, the
            way the GUI does -- walk up to config.yaml, then take each
            dependency's design/*.cic, plus the .cic beside this one.
            A cell that instantiates finished blocks needs them all or
            the render dies on the first unresolved reference; set
            False to pass `includes` alone.
        flightlines: Nets to draw FLIGHTLINES for -- each net's pins
            boxed and joined by a dashed line, over the layout that may
            or may not connect them. Pass the nets `checkroutes` calls
            open and the picture shows what has to be drawn and what is
            in the way. Pass ["*"] for every net with more than one pin.
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
    if auto_libs:
        includes = _auto_libs(cicfile) + includes

    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(prefix="cicpy_mcp_")
    try:
        os.chdir(tmpdir)
        rules = ciclib.Rules(techfile)
        design = ciclib.Design()
        design.fromJsonFilesWithDependencies(cicfile, includes)
        nets = list(flightlines or [])
        if nets == ["*"]:
            nets = _all_multi_pin_nets(design, cell)
        printer = ciclib.SvgPrinter(library, rules, 10, 100, 100,
                                    flightnets=nets)
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


def _auto_libs(cicfile):
    """Every other .cic this design might reference.

    The GUI already does this -- walk up to config.yaml and take each
    dependency's `design/*.cic` -- and a render that dies on the first
    unresolved cell is the same problem seen from the other end. The
    cell's own directory is added too, because a hierarchical build
    writes its subcells beside it in `design/<LIB>/`, one level below
    where a ciccreator library publishes.
    """
    from .gui.app import discover_libraries
    out = []
    try:
        out += discover_libraries(cicfile)
    except Exception as exc:
        log.warning(f"auto_libs: {exc}")
    here = os.path.dirname(os.path.abspath(cicfile))
    for pat in (os.path.join(here, "*.cic"),
                os.path.join(os.path.dirname(here), "*", "*.cic")):
        for f in sorted(glob.glob(pat)):
            if os.path.abspath(f) != os.path.abspath(cicfile):
                out.append(f)
    seen, uniq = set(), []
    for f in out:
        a = os.path.abspath(f)
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq


def _all_multi_pin_nets(design, cellname):
    """Every net with more than one pin in `cellname`, by port name."""
    cell = design.cells.get(cellname)
    if cell is None:
        return []
    seen = {}
    for child in getattr(cell, "children", []) or []:
        if not (hasattr(child, "isInstance") and child.isInstance()):
            continue
        sub = (getattr(child, "layoutcell", None)
               or getattr(child, "_cell_obj", None)
               or design.cells.get(getattr(child, "cell", "")))
        if sub is None:
            continue
        for c in getattr(sub, "children", []) or []:
            if hasattr(c, "isPort") and c.isPort():
                seen[c.name] = seen.get(c.name, 0) + 1
    return sorted(n for n, k in seen.items() if k > 1)


def _tech_layers(techfile):
    """{(gds number, datatype): (cicpy layer name, colour, material, z)}.

    Straight off the technology file -- the server carries no layer
    table of its own, same as every other tool here.
    """
    with open(techfile) as fh:
        tech = json.load(fh)
    order = {"well": 0, "diffusion": 1, "implant": 2, "poly": 3,
             "metal": 5, "cut": 20}
    out = {}
    for name, layer in tech.get("layers", {}).items():
        num, dt = layer.get("number"), layer.get("datatype")
        if num is None or dt is None:
            continue
        key = (int(num), int(dt))
        #- one GDS purpose carries several cicpy names (PDIFF, NDIFF,
        #- OD): keep the first drawing one, and never let a _pin win
        if key in out or name.endswith("_pin"):
            continue
        mat = layer.get("material") or ""
        z = order.get(mat, 4)
        if mat == "metal" and name[1:].isdigit():
            z = order["metal"] + int(name[1:])
        #- the technology file already says which layers are markers:
        #- "fill": "nofill". Those are boundaries, implants and wells
        #- -- filled, they bury the layout under one flat colour.
        fill = layer.get("fill") != "nofill"
        out[key] = (name, layer.get("color") or "grey", mat, z, fill)
    return out


@mcp.tool()
def render_gds(
    gdsfile: str,
    techfile: str,
    cell: str | None = None,
    top_only: bool = False,
    only_layers: list[str] | None = None,
    outlines: bool = True,
    title: str | None = None,
    height: int = 1200,
) -> Image:
    """Draw a GDS the way a layout engineer reads it, and return it inline.

    The companion to `render`, which draws the cic file cicpy wrote.
    This one draws what actually reached the GDS -- subcell contents
    included -- with one colour per technology layer and a legend that
    names the layers the way the sidecar does (M1..M5, not met1..met4).

    `top_only` is the mode to reach for when debugging routing: it
    draws only the paint the TOP cell owns and leaves the placed
    blocks as labelled outlines, so a hand written route is not lost
    among a hundred thousand transistor rectangles.

    Args:
        gdsfile: Path to the .gds file.
        techfile: Path to the technology file; supplies the GDS layer
            numbers, the colours and the layer names.
        cell: Cell to draw. Omit for the file's top cell.
        top_only: Draw only the top cell's own paint (routing view).
        only_layers: Restrict to these cicpy layer names, e.g.
            ["M3", "M4", "M5"]. Omit for every layer that has paint;
            layers the technology marks "nofill" (boundary, implant,
            well) are drawn as outlines rather than filled.
        outlines: Draw instance outlines. Always on when top_only.
        title: Title for the figure. Defaults to the cell name.
        height: Raster height in pixels.
    """
    try:
        import gdstk
    except ImportError:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "render_gds needs gdstk: pip install 'cicpy[mcp]'")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as _MPoly, Rectangle as _Rect

    style = _tech_layers(os.path.abspath(techfile))
    lib = gdstk.read_gds(os.path.abspath(gdsfile))
    cells = {c.name: c for c in lib.cells}
    if cell is None:
        tops = lib.top_level()
        if not tops:
            raise ValueError(f"no top cell in {gdsfile}")
        top = tops[0]
    else:
        if cell not in cells:
            raise ValueError(
                f"no cell {cell!r} in {gdsfile}; have "
                f"{', '.join(sorted(cells)[:20])}")
        top = cells[cell]

    keep = set(only_layers) if only_layers else None
    bylayer = collections.defaultdict(list)
    for poly in top.get_polygons(depth=0 if top_only else None):
        info = style.get((poly.layer, poly.datatype))
        if info is None:
            continue
        if keep is not None and info[0] not in keep:
            continue
        bylayer[(poly.layer, poly.datatype)].append(poly.points)

    bbox = top.bounding_box() or ((0, 0), (1, 1))
    (x1, y1), (x2, y2) = bbox
    span = max(x2 - x1, y2 - y1) or 1.0
    fig, ax = plt.subplots(
        figsize=(height / 100.0 * (x2 - x1) / span + 3, height / 100.0),
        dpi=100)

    if outlines or top_only:
        for ref in top.references:
            rb = ref.bounding_box()
            if rb is None:
                continue
            (rx1, ry1), (rx2, ry2) = rb
            ax.add_patch(_Rect((rx1, ry1), rx2 - rx1, ry2 - ry1,
                               fill=top_only, fc="#f0f0f0",
                               ec="#999999", lw=0.8, zorder=0))
            #- only label a block with room for the name: a strip of
            #- abutted standard cells turns into a stack of overlapping
            #- labels otherwise
            if top_only and (ry2 - ry1) > span / 25.0:
                nm = getattr(getattr(ref, "cell", None), "name", "")
                ax.text((rx1 + rx2) / 2.0, (ry1 + ry2) / 2.0, nm,
                        fontsize=7, ha="center", va="center",
                        color="#777777", zorder=1)

    for key in sorted(bylayer, key=lambda k: style[k][3]):
        name, color, mat, z, fill = style[key]
        alpha = 0.9 if mat == "cut" else (0.45 if fill else 0.7)
        for pts in bylayer[key]:
            ax.add_patch(_MPoly(pts, closed=True,
                                facecolor=color if fill else "none",
                                edgecolor=color, alpha=alpha,
                                linewidth=0.2 if fill else 0.5,
                                zorder=3 + z))
        ax.plot([], [], color=color, lw=6 if fill else 1.5, alpha=alpha,
                label=name)

    pad = span * 0.03
    ax.set_xlim(x1 - pad, x2 + pad)
    ax.set_ylim(y1 - pad, y2 + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("um")
    ax.set_ylabel("um")
    ax.set_title(title or (top.name + (" -- top-level paint only"
                                       if top_only else "")))
    if bylayer:
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
                  fontsize=8, frameon=False)
    fig.tight_layout()
    tmpdir = tempfile.mkdtemp(prefix="cicpy_mcp_")
    pngfile = os.path.join(tmpdir, top.name + ".png")
    fig.savefig(pngfile, bbox_inches="tight")
    plt.close(fig)
    with open(pngfile, "rb") as fh:
        data = fh.read()
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
            shorts.append(_strip_ansi(m.group(1)))
        #- both kinds of open. Matching only split_components dropped
        #- every net whose pins reach nothing at all -- the commonest
        #- kind, and the one that reads as "almost done" when counted
        #- wrong: 13 opens were reported as 4
        m = re.search(r"WARNING: OPEN (net=\S+ (?:split_components|unmatched_anchors)=[^\x1b]+)", l)
        if m:
            opens.append(_strip_ansi(m.group(1)))
        m = re.search(r"WARNING: {2}(BRIDGE [^\x1b]+)", l)
        if m and shorts:
            shorts.append("  " + _strip_ansi(m.group(1)))
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
def stackorder(spicefile: str, cell: str, terminal: str = "D",
               group: str = "", verbose: bool = False) -> str:
    """Which columns are interleaved, and what reordering them would buy.

    A rail down a column of parallel devices crosses every pin it
    passes, so a net whose pins on that terminal are interleaved with
    another net's cannot have one. That is decided by the order the
    devices sit in -- placement's business, not routing's -- and it is
    cheap to fix and expensive to discover: interleaving reads back as a
    short or an open with no hint of the cause, one regeneration per
    guess.

    This reads the netlist, so it can be asked before the first
    placement. Act on it with `orderByTerminalNet(<terminal>)` on the
    stack in afterPlace, before dummy fill and taps. Not on a series
    chain, where the order is what makes each link a neighbour of the
    next, and not on a matched pair, where the order is the matching.

    Args:
        spicefile: The netlist, e.g. work/xsch/<CELL>.spice.
        cell: The subcircuit to analyse.
        terminal: Which terminal a rail would sit on: D, G, S or B.
        group: Only this column, by netlist group name, e.g. "xnd".
        verbose: List the instances in each column too.
    """
    cmd = ["cicpy", "stackorder", spicefile, cell, "--terminal", terminal]
    if group:
        cmd += ["--group", group]
    if verbose:
        cmd += ["--verbose"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout.strip() or (proc.stderr.strip() or "no output")


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
    args = ["tracks", cicfile, techfile, cell]
    if layer:
        args += ["--layer", layer]
    if band:
        args += ["--band", band]
    if free:
        args += ["--free", free]
    return _run_cic(*args, includes=includes)


@mcp.tool()
def blockers(cicfile: str, techfile: str, cell: str, net: str, box: str,
             includes: list[str] | None = None) -> str:
    """What stops `net` from dropping a via column in `box`.

    Ask this when a route shorts and the track report looks clean. A
    wire of another net is space to route around; a PIN of another net
    is space that cannot be crossed at all -- and the collision is
    rarely on one layer. A trunk on M4 and a pin on M1 never share a
    track, so a same-layer check reports nothing. What collides is the
    via COLUMN: a route reaching a pin comes down through every layer at
    that x, and any other net's pin in the way is shorted.

    Every routing failure measured so far has been this, and nothing
    in the old router could see it.

    Args:
        cicfile: Path to the .cic holding the layout.
        techfile: Path to the technology file.
        cell: The cell to inspect.
        net: The net that wants to route there.
        box: "X1:X2:Y1:Y2", the column to test.
        includes: Other .cic files the design references.
    """
    return _run_cic("blockers", cicfile, techfile, cell,
                    "--net", net, "--box", box, includes=includes)


@mcp.tool()
def findroute(cicfile: str, techfile: str, cell: str, net: str,
              start: str, stop: str,
              includes: list[str] | None = None) -> str:
    """Search a path for `net`, and report it WITHOUT drawing anything.

    A shortest path over the track grid that knows what is in the way,
    including other nets' pins. Use it to answer "is there a way through
    and what does it cost" before committing geometry -- the old loop
    was to draw a guess, regenerate, and read the short report, which
    costs a full rebuild per guess.

    A failure is a diagnosis: it reports how far the search got and what
    blocked it, not just "no route".

    Args:
        cicfile: Path to the .cic holding the layout.
        techfile: Path to the technology file.
        cell: The cell to route in.
        net: Net to route.
        start: "X,Y,LAYER", e.g. "270000,104000,M3".
        stop: "X,Y,LAYER".
        includes: Other .cic files the design references.
    """
    return _run_cic("findroute", cicfile, techfile, cell,
                    "--net", net, "--start", start, "--stop", stop,
                    includes=includes)


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
