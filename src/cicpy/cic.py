######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-13
## ###################################################################
##  The MIT License (MIT)
## 
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
## 
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
## 
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##  
######################################################################

import importlib
import click
import os, re, sys
import cicpy as cic
import json
import cicspi
import yaml
import logging


class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[1;31m' # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

log = logging.getLogger("spi2mag")


def load_design(cicfile, includes=()):
    design = cic.Design()
    design.fromJsonFilesWithDependencies(cicfile, includes)
    return design

@click.group()
@click.pass_context
def cli(ctx):
    """ Python toolbox for Custom Integrated Circuit Creator (ciccreator). """
    ctx.ensure_object(dict)
    handler = logging.StreamHandler()
    formatter = ColorFormatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    pass

@cli.command("transpile")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("library")
@click.option("--layskill",is_flag=True,help="Write Skill Layout file ")
@click.option("--schskill",is_flag=True,help="Write Skill Schematic file ")
@click.option("--winfo",is_flag=True,help="Write Info file [ALPHA]")
@click.option("--rinfo",default="",help="Read Info file [ALPHA]")
@click.option("--verilog",is_flag=True,help="Write verilog file [EXPERIMENTAL]")
@click.option("--spice",is_flag=True,help="Write spice file ")
@click.option("--xschem",is_flag=True,help="Write xschem schematics")
@click.option("--magic",is_flag=True,help="Write magic layout")
@click.option("--smash",default=None,help="List of transistors to smash schematic hierarchy")
@click.option("--exclude",default="",help="Regex of cells to ignore")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def transpile(ctx,cicfile,techfile,library,layskill,schskill,winfo,rinfo,verilog,spice,xschem,magic,smash,exclude,includes):
    """Translate .cic file into another file format (SKILL,SPECTRE,SPICE)"""

    rules = cic.Rules(techfile)
    design = load_design(cicfile, includes)



    if(layskill):
        la = cic.SkillLayPrinter(library,rules)
        #la.exclude = exclude
        la.print(design)

    if(schskill):
        sc = cic.SkillSchPrinter(library,rules,smash)
        #sc.exclude = exclude
        sc.print(design)

    if(winfo):
        obj = cic.CellInfoPrinter(library,rules)
        sc.exclude = exclude
        obj.print(design)

    if(verilog):
        obj = cic.VerilogPrinter(library,rules)
        obj.exclude = exclude
        obj.print(design)

    if(spice):
        obj = cic.SpicePrinter(library,rules)
        #obj.exclude = exclude

        #- Print ngspice simulation netlist (.spice)
        obj.print(design)

        #- Print cdl netlist (.spi)
        obj.lastname = ".spi"
        obj.ngspice = False
        obj.print(design)

    if(xschem):
        obj = cic.XschemPrinter(library,rules)
        obj.exclude = exclude
        obj.print(design)

    if(magic):
        obj = cic.MagicPrinter(library,rules)
        obj.exclude = exclude
        obj.print(design)


@cli.command("jcell")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--child",default="",help="Show children")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def jcell(ctx,cicfile,techfile,cell,child,includes):
    """Extract a cell from .cic """

    rules = cic.Rules(techfile)

    design = load_design(cicfile, includes)


    if(cell in design.jcells):
        obj = design.jcells[cell]
        if(child == "None"):
            obj["children"] = {}
        elif(child):
            nl = list()
            for c in obj["children"]:
                if(c["class"] == child):
                    nl.append(c)
            obj["children"] = nl

        print(json.dumps(obj,indent=4))
    else:
        print("\n".join(design.cellnames))


@cli.command("place")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("layoutfile")
@click.option("--circuit", default="diffpair")
@click.option("--pattern", default="")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def place(ctx,cicfile,techfile,layoutfile,circuit,pattern,includes):
    """[Deprecated] Place a bunch of transistors according to pattern, outputs SKILL"""

    rules = cic.Rules(techfile)

    design = load_design(cicfile, includes)


    placer = cic.Placer(design,layoutfile,pattern)
    if(circuit == "diffpair"):
        placer.placeDiffPair()
    elif(circuit == "currentmirror"):
        print("TODO: Implement current mirror specific placer")
    elif(circuit == "vertical"):
        placer.placeVertical()
    elif(circuit == "horizontal"):
        placer.placeHorizontal()
    else:
        print(f"Could not find placer '{circuit}', using vertical")
        placer.place()
    placer.toCsv(layoutfile.replace(".csv","_place.csv"))
    placer.toSkill(layoutfile.replace(".csv",".il"))



@cli.command("minecraft")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--child",default="",help="Show children")
@click.option("--x",default=0,help="X coordinate")
@click.option("--y",default=0,help="Y coordinate")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def minecraft(ctx,cicfile,techfile,cell,child,x,y,includes):
    """Make a mincraft script *.mc from *.cic """

    rules = cic.Rules(techfile)

    design = load_design(cicfile, includes)

    if(cell in design.cells):
        cell = design.cells[cell]

        mc = cic.MinecraftCellPrinter(rules,design,cell,x,y)
        buff = mc.clear()
        buff += mc.print()
        buff += mc.printCuts()

        with open(cell.name + ".mc","w") as fo:
            fo.write(buff)

    else:
        print("\n".join(design.cellnames))

@cli.command("svg")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("library")
@click.option("--scale",default=10,help="Scale")
@click.option("--x",default=100,help="X offset")
@click.option("--y",default=100,help="Y offset")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def svg(ctx,cicfile,techfile,library,scale,x,y,includes):
    """Make an SVG"""

    rules = cic.Rules(techfile)

    design = load_design(cicfile, includes)

    svg = cic.SvgPrinter(library,rules,scale,x,y)
    svg.print(design)

@cli.command("sch2mag")
@click.pass_context
@click.argument("lib")
@click.argument("cell")
@click.option("--libdir",default="../design/",help="Default directory of designs")
@click.option("--techlib",default="sky130A",help="Technology library")
@click.option("--xspace",default="0",help="Group X space")
@click.option("--yspace",default="0",help="Group Y space")
@click.option("--gbreak",default="10",help="Increment Y every gbreak groups")
@click.option("--check-connectivity", is_flag=True, help="Run full connectivity check after routing")
@click.option("--strict", is_flag=True, help="Check connectivity after every route and stop at the first short")
@click.option("--hier", is_flag=True,
              help="The top INSTANTIATES its subcells instead of "
                   "containing their devices. Run sch2subcells first.")
def xsch2mag(ctx,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity,strict,hier):
    """Netlist a xschem to spice, and load file to Magic"""

    os.system(f"make xsch LIB={lib} CELL={cell}")

    spi = "xsch/" + cell + ".spice"

    _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity,strict,
             hier=hier)



@cli.command("sch2subcells")
@click.pass_context
@click.argument("lib")
@click.argument("cell")
@click.option("--libdir",default="../design/",help="Default directory of designs")
@click.option("--techlib",default="sky130A",help="Technology library")
@click.option("--xspace",default="0",help="Group X space")
@click.option("--yspace",default="0",help="Group Y space")
@click.option("--gbreak",default="10",help="Increment Y every gbreak groups")
@click.option("--subcell","subcells",multiple=True,
              help="Write only this subcell. Repeatable. Matches the "
                   "subcell's short name (p_sw) or its cell name "
                   "(MYCELL_P_SW).")
def sch2subcells(ctx,lib,cell,libdir,techlib,xspace,yspace,gbreak,subcells):
    """Generate a cell per subcell: .mag, .cic, .sch and .sym.

    Step one of two. Place the cell exactly as sch2mag would, then write
    out each SUBCELL as a cell of its own and stop -- the parent's own
    .mag is not written and not touched.

    The point is that a subcell becomes a thing on disk that can be
    verified by itself, before anything is built on top of it. Run this,
    check each one with drc and lvs, and only then build the parent.

    A subcell is any CellGroup the design marks with ``subcell = True``,
    and failing that every stack -- a column of devices being the
    decomposition that needs no thought. Nothing here is confined to
    stacks: mark a differential pair spread over two columns, or a
    whole side, and it is published the same way.

    Which cells get written is taken from the plan, BY NAME. The
    schematics used to come from a second `transpile --xschem` with a
    negative lookahead over the cell name, which the Makefile had to
    describe as "not optional" because getting it wrong overwrote the
    hand-drawn parent schematic with a generated one.
    """
    os.system(f"make xsch LIB={lib} CELL={cell}")
    spi = "xsch/" + cell + ".spice"
    _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,
             subcells_only=True,only_subcells=subcells)


@cli.command("spi2mag")
@click.pass_context
@click.argument("spi")
@click.argument("lib")
@click.argument("cell")
@click.option("--libdir",default="../design/",help="Default directory of designs")
@click.option("--techlib",default="sky130A",help="Technology library")
@click.option("--xspace",default="0",help="Group X space")
@click.option("--yspace",default="0",help="Group Y space")
@click.option("--gbreak",default="10",help="Increment Y every gbreak groups")
@click.option("--check-connectivity", is_flag=True, help="Run full connectivity check after routing")
@click.option("--strict", is_flag=True, help="Check connectivity after every route and stop at the first short")
def spi2mag(ctx,spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity,strict):
    """Translate a SPICE file to Magic"""
    _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity,strict)



def _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity=False,strict=False,
             subcells_only=False,only_subcells=(),hier=False):

    techfile = f"../tech/cic/{techlib}.tech"
    log.info(f"Loading rules {techfile}")
    rules = cic.Rules(techfile)

    log.info(f"Finding Magic cells in {libdir}")
    design = cic.MagicDesign(techlib,rules)
    design.scanLibraryPath(libdir)
    design.primitive_cache_dir = os.path.join(libdir, lib, "_cicpy_primitives")
    try:
        from cicpy.pdk import register_default_providers
        register_default_providers(design)
    except Exception as ex:
        log.warning(f"Could not register primitive providers: {ex}")

    log.info(f"Reading {spi}")
    lcell = design.readFromSpice(spi,cell)

    if("," in gbreak):
        lcell.place_gbreak = gbreak.split(",")
    else:
        lcell.place_gbreak = [int(gbreak)]

    if("," in xspace):
        lcell.place_xspace = list(map(lambda x: int(x),xspace.split(",")))
    else:
        lcell.place_xspace = [int(xspace)]

    if("," in yspace):
        lcell.place_yspace = list(map(lambda x: int(x),yspace.split(",")))
    else:
        lcell.place_yspace = [int(yspace)]


    lcell.dirname = libdir + lib + os.path.sep

    _ensure_default_pycell(lcell.dirname, lcell.name)

    pycell = None
    pycellData = None
    if(os.path.exists(lcell.dirname + lcell.name + ".py")):
        sys.path.append(lcell.dirname)
        pycell = importlib.import_module(lcell.name)
        if(hasattr(pycell,"data")):
            pycellData = pycell.data

    lcell.strict_route = strict
    lcell.layout(pycell,pycellData)

    if check_connectivity:
        _report_route_shorts(lcell)
        _report_connectivity(lcell)

    #- Add cuts after the layout has been routed
    design.addCuts()

    if subcells_only:
        _write_subcells(design,lcell,libdir,lib,rules,only_subcells)
        return

    if hier:
        _hierarchify(design,lcell,log)

    obj = cic.MagicPrinter(libdir + lib,rules)
    #- The parent step does not write subcells. Both commands used to
    #- write the same eight .mag files and only agreed by luck: the
    #- parent's copies are made by the design's afterPaint, mid layout,
    #- while sch2subcells rebuilds them as its own authoritative pass.
    #- Whichever ran last won, silently. One owner each.
    #-
    #- The .cic still carries them, so the parent remains a complete
    #- description and the route tools can be pointed at either.
    try:
        from cicpy.core.mazerouter import plan_subcells
        subnames = [e["name"] for e in plan_subcells(lcell)]
    except Exception:
        subnames = []
    if subnames:
        obj.exclude = "^(?:" + "|".join(re.escape(n) for n in subnames) + ")$"
    obj.print(design)
    #for m in design.maglib.values():
        #if(m._lay is not None):

    cicfile = libdir + lib + os.path.sep + lcell.name + ".cic"
    obj = design.toJson()

    #- Same boundary check as MagicPrinter: nothing off grid leaves cicpy
    cic.checkJsonOnGrid(obj,rules,output=cicfile)

    with open(cicfile,"w") as fo:
        fo.write(json.dumps(obj,indent=4))
        #fo.write(json.dumps(design.maglib["JNWTR_RPPO2"]._lay.toJson(),indent=4))


def _keep_only(names):
    """An exclude regex that keeps exactly `names` and nothing else.

    DesignPrinter filters by excluding, so "print only these" has to be
    said backwards. Built from the real names rather than a prefix: a
    prefix pattern also matches the parent, and the difference between
    the two is a generated schematic written over a hand-drawn one.
    """
    if not names:
        return ".*"
    alts = "|".join(re.escape(n) for n in sorted(names))
    return f"^(?!(?:{alts})$).*"


def _hierarchify(design,lcell,log):
    """The top references its subcells instead of containing them.

    The restructuring step write_stack_cells deliberately defers: every
    device instance that belongs to a subcell leaves the top, and one
    Instance of the subcell arrives in its place. Because a published
    subcell keeps the parent's absolute coordinates, that Instance sits
    at the origin with the identity transform and the geometry lands
    exactly where the flat devices were.

    The top's own routing -- rings, straps, inter-subcell routes -- is
    untouched. Routes whose geometry was COPIED into a subcell stay in
    the top as well: the copies overlap their originals exactly, on the
    same net, which costs bytes and nothing else, and removing the
    originals means proving for each that every rect went along, which
    is a verification burden this step does not need yet.
    """
    from cicpy.core.mazerouter import plan_subcells
    from cicpy.core.instance import Instance

    plan = plan_subcells(lcell)
    if not plan:
        log.warning(f"{lcell.name}: no subcells; nothing to hierarchify")
        return
    missing = [e["name"] for e in plan
               if e["name"] not in getattr(design, "cells", {})]
    if missing:
        log.error(f"{lcell.name}: subcells not registered: "
                  f"{', '.join(missing)}. Run sch2subcells first; "
                  f"keeping the flat top.")
        return

    leaving = set()
    for entry in plan:
        leaving.update(entry["instances"])

    def _prune(node):
        kept = []
        for ch in getattr(node, "children", []) or []:
            if ch is None:
                continue
            if (hasattr(ch, "isInstance") and ch.isInstance()
                    and (getattr(ch, "instanceName", "") or "") in leaving):
                continue
            if hasattr(ch, "children"):
                _prune(ch)
            kept.append(ch)
        node.children = kept

    _prune(lcell)

    for entry in plan:
        sub = design.cells[entry["name"]]
        inst = Instance()
        inst.design = design
        #- name too: Cell.isEmpty is "has no name", and printReference
        #- drops an empty instance without a word
        inst.name = entry["name"]
        inst.cell = entry["name"]
        inst.instanceName = f"x{entry['stack']}"
        inst.angle = "R0"
        inst.xcell = 0
        inst.ycell = 0
        inst.layoutcell = sub
        inst._cell_obj = sub
        #- the subcell keeps the parent's absolute coordinates until
        #- the restructuring step; xcell cancels x1 so the use maps
        #- identity
        inst.setRect(sub)
        inst.xcell = -int(sub.x1)
        inst.ycell = -int(sub.y1)
        lcell.add(inst)
        log.info(f"{lcell.name}: x{entry['stack']} = {entry['name']}")


def _subcell_pycell_template(name, entry):
    return f'''"""{name}: this subcell's own layout hooks.

Generated once by `cicpy sch2subcells`, then yours: edit and commit.

Both hooks run in the parent, between its afterPlace and beforeRoute,
with `layout` the parent LayoutCell and `entry` this subcell's plan:
    entry["instances"]  the instance names in this subcell
    entry["ports"]      its boundary nets
    entry["internal"]   nets wholly inside it
    entry["type"]       stack | diffpair | mirror, from {name.split("_")[0]}.yaml
"""


def beforePlace(layout, entry):
    """Adjust this subcell's placement before anything routes."""


def beforeRoute(layout, entry):
    """Route this subcell's internal nets.

    Return True to claim the subcell as ROUTED -- the built-in stack
    router will then leave it alone. Return None to let the built-in
    router handle it, which is the right default.
    """
'''


def _ensure_subcell_pycells(lcell, plan, log):
    """A .py per subcell, generated when missing, never overwritten."""
    import os
    dirname = getattr(lcell, "dirname", "") or ""
    made = []
    for entry in plan:
        path = os.path.join(dirname, entry["name"] + ".py")
        if os.path.exists(path):
            continue
        with open(path, "w") as fo:
            fo.write(_subcell_pycell_template(entry["name"], entry))
        made.append(entry["name"])
    if made:
        log.info(f"pycell stubs written (edit and commit them): "
                 f"{', '.join(made)}")


def _write_subcells(design,lcell,libdir,lib,rules,only=()):
    """Write a cell per subcell and nothing else.

    `only` narrows WHAT IS WRITTEN, never what is built: the cell is
    placed and routed exactly as it always is, so a subcell taken on its
    own is the same subcell it would be in a full run. Anything else
    would make iterating on one a different experiment from the real
    thing.
    """
    from cicpy.core.mazerouter import plan_subcells, write_stack_cells

    plan = plan_subcells(lcell)
    if not plan:
        log.warning(f"{lcell.name}: no subcells found; nothing to write")
        return

    if only:
        want = {o.upper() for o in only}
        chosen = [e for e in plan
                  if e["name"].upper() in want or e["stack"].upper() in want]
        if not chosen:
            have = ", ".join(sorted(e["stack"] for e in plan))
            raise click.ClickException(
                f"no subcell matches {', '.join(only)}. This cell has: {have}")
        plan = chosen

    #- REBUILD, do not reuse. A design's own afterPaint may already have
    #- published these, from whatever state the layout was in at that
    #- moment; write_stack_cells then leaves an already registered cell
    #- alone. Clearing them first is what makes THIS the authoritative
    #- pass rather than a no-op behind the design's back.
    for entry in plan:
        nm = entry["name"]
        getattr(design,"cells",{}).pop(nm,None)
        names_list = getattr(design,"cellnames",None)
        if names_list is not None and nm in names_list:
            names_list.remove(nm)
    write_stack_cells(lcell,design=design,plan=plan,log=log)

    _ensure_subcell_pycells(lcell, plan, log)

    names = [e["name"] for e in plan]
    keep = _keep_only(names)
    log.info(f"{lcell.name}: writing {len(names)} subcell"
             f"{'s' if len(names) != 1 else ''}")

    obj = cic.MagicPrinter(libdir + lib,rules)
    obj.exclude = keep
    obj.print(design)

    obj = cic.XschemPrinter(libdir + lib,rules)
    obj.exclude = keep
    #- The printer must KNOW every referenced cell before anything
    #- prints. symbolAndWrite returns SILENTLY when an instantiated
    #- cell is missing from printer.cells -- no wires, no error, and
    #- the position counter never advances, so the output is a pile of
    #- symbols at one spot that netlists without complaint. It happened
    #- here because sch2mag's design holds the devices in maglib, not
    #- in design.cells; their SUBCKTS are in the cicspi registry from
    #- the netlist that placed them, and that is what the printer
    #- actually reads (instcell.ckt.nodes), so stand-ins carrying the
    #- registry subckt are the whole requirement.
    obj.cells.update(getattr(design, "cells", {}))
    referenced = set()
    for entry in plan:
        cellobj = design.cells.get(entry["name"])
        ckt = getattr(cellobj, "ckt", None)
        for inst in (getattr(ckt, "instances", None) or []):
            nm = getattr(inst, "subcktName", "")
            if nm:
                referenced.add(nm)
    #- and every sibling library's symbols are findable, so a device
    #- cell resolves to ITS OWN library. Without this the printer only
    #- saw symbols in the library being written, which required local
    #- COPIES of every device symbol -- 392 of them, in one repo,
    #- committed by accident -- and stamped the generated schematics
    #- with references to the copies instead of the originals.
    import glob as _glob
    for symfile in _glob.glob(os.path.join(libdir, "*", "*.sym")):
        if symfile not in obj.lib_symbols:
            obj.lib_symbols.append(symfile)
    for nm in sorted(referenced):
        if nm in obj.cells:
            continue
        sub = cicspi.Subckt.getSubckt(nm)
        if sub is None:
            log.warning(f"{nm}: no subckt in the registry; its instances "
                        f"will print without wires")
            continue
        stand_in = cic.Cell(nm)
        stand_in.ckt = sub
        #- the library the symbol actually lives in, preferring a
        #- sibling over the library being written: the reference
        #- embedded in the .sch is <libname>/<cell>.sym, and it should
        #- name the device library, not a local copy
        own = os.path.join(libdir, lib, nm + ".sym")
        for symfile in sorted(_glob.glob(os.path.join(libdir, "*",
                                                      nm + ".sym"))):
            if os.path.abspath(symfile) != os.path.abspath(own):
                stand_in.libpath = os.path.dirname(symfile)
                break
        obj.cells[nm] = stand_in
    obj.print(design)

    #- The CUT cells travel with every subcell. A route that changes
    #- layer places an InstanceCut referring to cut_<A><B>_NxM, and a
    #- .cic that does not define those cells resolves the via to
    #- nothing -- so the route checker reads the corridor as empty and
    #- says the column is free. A wrong "nothing blocks" is worse than
    #- an error, and they are a few hundred bytes each.
    from cicpy.core.cut import Cut as _Cut
    cuts = {n: c for n, c in getattr(design,"cells",{}).items()
            if isinstance(c, _Cut)}

    for entry in plan:
        name = entry["name"]
        cellobj = design.cells.get(name)
        if cellobj is None:
            continue
        cicfile = libdir + lib + os.path.sep + name + ".cic"
        one = cic.Design()
        one.cells = dict(cuts)
        one.cells[name] = cellobj
        if hasattr(one,"cellnames"):
            #- cuts first: defined before they are used
            one.cellnames = sorted(cuts) + [name]
        try:
            with open(cicfile,"w") as fo:
                fo.write(json.dumps(one.toJson(),indent=4))
        except Exception as ex:
            log.warning(f"{name}: could not write {cicfile}: {ex}")
        log.info(f"  {name}: {' '.join(entry['ports']) or '(no ports)'}")

    #- THE HIERARCHICAL NETLIST: the top as instances of its subcells,
    #- every connection a parent net name, every subckt the generated
    #- one. This is what a hierarchical placement flow places from.
    hier = [f"** generated by cicpy sch2subcells: {lcell.name} as subcells"]
    for entry in plan:
        cellobj = design.cells.get(entry["name"])
        for line in (getattr(cellobj, "cic_subckt", None) or []):
            hier.append(line)
        hier.append("")
    top_ports = list(getattr(getattr(lcell, "ckt", None), "nodes", None)
                     or [])
    hier.append(f".subckt {lcell.name}_HIER {' '.join(top_ports)}")
    for entry in plan:
        ports = list(entry["ports"])
        hier.append(f"x{entry['stack']} {' '.join(ports)} {entry['name']}")
    hier.append(".ends")
    hierfile = libdir + lib + os.path.sep + lcell.name + "_HIER.spice"
    with open(hierfile, "w") as fo:
        fo.write("\n".join(hier) + "\n")
    log.info(f"  hierarchical netlist: {hierfile}")

    #- Say how to check them. The route tools need the device library
    #- passed in, and working that out from scratch is a papercut every
    #- single time.
    log.info(f"  check one with:  cicpy svg <libdir>/{lib}/<SUBCELL>.cic "
             f"<techfile> <SUBCELL> --I <device-library>.cic")


def _ensure_default_pycell(dirname, cell):
    pycell_path = os.path.join(dirname, cell + ".py")
    if os.path.exists(pycell_path):
        return

    os.makedirs(dirname, exist_ok=True)
    with open(pycell_path, "w") as fo:
        fo.write(_default_pycell_template(cell))
    log.info(f"Created default pycell {pycell_path}")


def _default_pycell_template(cell):
    return f'''"""cicpy layout hooks for {cell}.

Uncomment the hooks you need. Each hook receives the LayoutCell object
as ``layout``.
"""


# def beforePlace(layout):
#     pass


# def afterPlace(layout):
#     pass


# def beforeRoute(layout):
#     pass


# def afterRoute(layout):
#     pass


# def beforePaint(layout):
#     pass


# def afterPaint(layout):
#     pass


# def beforePorts(layout):
#     pass


# def afterPorts(layout):
#     pass
'''


def _format_route_desc(short):
    routes = short.get("routes", [])
    if not routes:
        return "none"

    external = [route for route in routes if not route.get("debug_internal", False)]
    if external:
        routes = external

    primary = routes[0]
    desc = (
        f"{primary['name']}[{primary['layer']} {primary['route']} {primary['options']}]"
        + (f" cmd={primary['debug_command']}" if primary.get("debug_command") else "")
        + (f" at {primary['debug_callsite']}" if primary.get("debug_callsite") else "")
    )
    extra = len(routes) - 1
    if extra > 0:
        desc += f" (+{extra} more routes)"
    return desc


def _report_route_shorts(lcell):
    try:
        result = lcell.checkRouteShorts()
    except Exception as exc:
        log.warning(f"Route short report failed for {lcell.name}: {exc}")
        return

    shorts = result.get("shorts", [])
    log.info(
        f"Route short report for {lcell.name}: "
        f"shorts={len(shorts)} components={result.get('component_count', 0)} "
        f"shapes={result.get('shape_count', 0)}"
    )

    for short in shorts:
        bounds = short["bounds"]
        log.warning(
            f"ROUTE SHORT component={short['component']} nets={','.join(short['nets'])} "
            f"bounds=({bounds.x1},{bounds.y1})-({bounds.x2},{bounds.y2}) rects={short['rect_count']} "
            f"routes={_format_route_desc(short)}"
        )


def _report_connectivity(lcell):
    try:
        result = lcell.checkConnectivity()
    except Exception as exc:
        log.warning(f"Connectivity report failed for {lcell.name}: {exc}")
        return

    shorts = result.get("shorts", [])
    opens = result.get("opens", [])
    log.info(
        f"Connectivity report for {lcell.name}: "
        f"shorts={len(shorts)} opens={len(opens)} "
        f"components={result.get('component_count', 0)} shapes={result.get('shape_count', 0)}"
    )

    for short in shorts:
        bounds = short["bounds"]
        log.warning(
            f"SHORT component={short['component']} nets={','.join(short['nets'])} "
            f"bounds=({bounds.x1},{bounds.y1})-({bounds.x2},{bounds.y2}) rects={short['rect_count']} "
            f"routes={_format_route_desc(short)}"
        )
        for bridge in short.get("bridges", ()):
            log.warning("  " + cic.LayoutCell.describeBridge(bridge))

    for open_net in opens:
        if open_net["type"] == "split":
            log.warning(f"OPEN net={open_net['net']} split_components={open_net['components']}")
        else:
            log.warning(f"OPEN net={open_net['net']} unmatched_anchors={open_net['anchors']}")





@cli.command("stackorder")
@click.pass_context
@click.argument("spicefile")
@click.argument("cell")
@click.option("--terminal",default="D",help="Which terminal the rail would sit on")
@click.option("--group",default="",help="Only this column, e.g. n_load")
@click.option("--verbose",is_flag=True,help="List the instances too")
def stackorder(ctx,spicefile,cell,terminal,group,verbose):
    """Which columns are interleaved, and what reordering them would buy.

    A rail down a column crosses every pin it passes, so a net whose
    pins are interleaved with another's cannot have one. That is the
    device order, which placement decides. Ask before placing rather
    than reading it back out of a short.
    """
    import cicspi
    from cicpy.core import stackorder as so
    sp = cicspi.SpiceParser()
    sp.parseFile(spicefile)
    if(cell not in sp):
        log.error(f"Could not find {cell} in {spicefile}")
        raise SystemExit(2)
    rows = so.analyse(sp[cell], terminal, [group] if group else None)
    click.echo(so.report(rows, verbose))


@cli.command("checkroutes")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--layer",default="",help="Only anchor nets on this layer")
def checkroutes(ctx,cicfile,techfile,cell,includes,layer):
    """Check a cell in a .cic for shorts and opens.

    The same geometric connectivity analysis the layout GUI shows and
    that spi2mag --check-connectivity runs, but reading a .cic that is
    already on disk instead of re-running placement. That makes it
    usable on a ciccreator library, where re-placing the cell would
    replace the layout being checked rather than judge it.
    """
    cic.Rules(techfile)
    design = load_design(cicfile, includes)

    if(cell not in design.cells):
        log.error(f"Could not find cell {cell} in {cicfile}")
        raise SystemExit(2)

    lcell = design.cells[cell]
    if(not hasattr(lcell,"checkConnectivity")):
        log.error(f"{cell} is a {lcell.__class__.__name__}, which carries no connectivity")
        raise SystemExit(2)

    result = lcell.checkConnectivity(layer)
    shorts = result.get("shorts",[])
    opens = result.get("opens",[])

    _report_connectivity(lcell)

    if(shorts or opens):
        raise SystemExit(1)
    log.info(f"{cell}: no shorts, no opens")


@cli.command("tracks")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--layer",default="",help="Only this layer")
@click.option("--band",default="",help="Only tracks whose coordinate is in LO:HI")
@click.option("--free",default="",help="Report tracks free over the span LO:HI")
@click.option("--verbose",is_flag=True,help="List free tracks too")
def tracks(ctx,cicfile,techfile,cell,includes,layer,band,free,verbose):
    """Report which routing tracks are occupied, and by what.

    A route is placed with a track number that is an offset from the
    net's own pins, so two nets in the same column land on each other at
    the same number and neither can tell. Finding that out by drawing it
    and reading the short report costs a regeneration per guess. This
    answers the question directly: which corridor is free, and where.
    """
    cic.Rules(techfile)
    design = load_design(cicfile, includes)
    if(cell not in design.cells):
        log.error(f"Could not find cell {cell} in {cicfile}")
        raise SystemExit(2)

    from cicpy.core.trackmap import TrackMap
    tm = TrackMap(design.cells[cell]).build()

    b = None
    if(band):
        lo,hi = band.split(":")
        b = (float(lo), float(hi))

    if(free):
        lo,hi = free.split(":")
        for lname in sorted(tm.tracks):
            if(layer and lname != layer):
                continue
            idx = tm.free_between(lname, float(lo), float(hi),
                                  b[0] if b else None, b[1] if b else None)
            coords = [int(tm.tracks[lname][i].coord) for i in idx]
            print(f"{lname}: {len(idx)} tracks free over {lo}..{hi}")
            print("   " + ", ".join(f"t{i}@{c}" for i,c in zip(idx,coords)))
        return

    print(tm.report(layer=layer or None, band=b, verbose=verbose))


@cli.command("blockers")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--net",required=True,help="The net that wants to route here")
@click.option("--box",required=True,help="X1:X2:Y1:Y2, the via column to test")
def blockers(ctx,cicfile,techfile,cell,includes,net,box):
    """What stops NET from dropping a via column in BOX.

    A wire of another net is space to route around; a PIN of another net
    is space that cannot be crossed at all. And the collision is rarely
    on one layer: a trunk on M4 and a pin on M1 never share a track, so
    a same-layer check reports nothing. What collides is the via column
    -- a route reaching a pin comes down through every layer at that x,
    and any other net's pin in the way is shorted.

    This asks that question directly, before anything is drawn.
    """
    cic.Rules(techfile)
    design = load_design(cicfile, includes)
    if(cell not in design.cells):
        log.error(f"Could not find cell {cell} in {cicfile}")
        raise SystemExit(2)
    from cicpy.core.trackmap import TrackMap
    tm = TrackMap(design.cells[cell], block_pins=True).build()
    try:
        x1,x2,y1,y2 = [float(v) for v in box.split(":")]
    except ValueError:
        log.error("--box wants X1:X2:Y1:Y2")
        raise SystemExit(2)
    hits = tm.column_blockers(net, x1, x2, y1, y2)
    if not hits:
        print(f"{net}: nothing blocks the column {box}")
        return
    seen = set()
    print(f"{net}: {len(hits)} blocking pin spans in {box}")
    for other, coord, s0, s1 in hits:
        key = (other, coord, s0, s1)
        if key in seen:
            continue
        seen.add(key)
        print(f"   {other:16s} at {coord}  span {s0}..{s1}")


@cli.command("findroute")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--net",required=True,help="Net to route")
@click.option("--start",required=True,help="X,Y,LAYER")
@click.option("--stop",required=True,help="X,Y,LAYER")
def findroute(ctx,cicfile,techfile,cell,includes,net,start,stop):
    """Search a path for NET, and report it without drawing anything.

    The search knows what is in the way, including other nets' PINS,
    which the route.py router does not model at all. It draws nothing:
    the point is to be able to ask "is there a way through, and what
    does it cost" before committing geometry.

    A failure is a diagnosis, not a shrug -- it reports how far the
    search got and what was blocking.
    """
    cic.Rules(techfile)
    design = load_design(cicfile, includes)
    if(cell not in design.cells):
        log.error(f"Could not find cell {cell} in {cicfile}")
        raise SystemExit(2)
    from cicpy.core.trackmap import TrackMap
    from cicpy.core.mazerouter import MazeRouter, Blocked

    def _node(text):
        parts = text.split(",")
        if len(parts) != 3:
            log.error("--start/--stop want X,Y,LAYER")
            raise SystemExit(2)
        return (int(float(parts[0])), int(float(parts[1])), parts[2].strip())

    tm = TrackMap(design.cells[cell], block_pins=True).build()
    r = MazeRouter(tm, net)
    a, b = _node(start), _node(stop)
    try:
        path = r.search(a, b, r.manhattan_heuristic(r.snap(b)))
    except Blocked as e:
        print(f"{net}: BLOCKED")
        print(f"   {e}")
        print(f"   nodes explored: {e.reached}")
        for other, coord, s0, s1 in e.blockers[:10]:
            print(f"   blocker {other} at {coord} span {s0}..{s1}")
        raise SystemExit(1)
    runs, vias = r.segments(path)
    print(f"{net}: path found, {len(path)} nodes -> {len(runs)} runs, {len(vias)} vias")
    for layer,x1,y1,x2,y2 in runs:
        print(f"   run {layer:3s} {x1},{y1} -> {x2},{y2}")
    for la,lb,x,y in vias:
        ok = "ok" if r.via_is_free(x,y) else "BLOCKED"
        print(f"   via {la}->{lb} at {x},{y}  [{ok}]")


@cli.command("gui")
@click.pass_context
@click.argument("cicfile")
@click.option("--tech","techfile",default=None,help="Tech file (.tech). Auto-discovered from <ipdir>/tech/cic/*.tech if omitted.")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--no-auto-libs",is_flag=True,help="Disable auto-discovery of dependency libraries via the IP's config.yaml.")
@click.option("--rerun-cmd",default=None,help="Shell command to rerun spi2mag (Ctrl+R / auto on .py change). Default: 'make' in IP root.")
@click.option("--rerun-cwd",default=None,help="Working directory for --rerun-cmd. Default: IP root (dir with config.yaml).")
def gui(ctx,cicfile,techfile,includes,no_auto_libs,rerun_cmd,rerun_cwd):
    """Open a Qt viewer on a .cic file (PySide6 required: pip install 'cicpy[gui]')."""
    from cicpy.gui.app import run
    run(cicfile, techfile=techfile, includes=includes, auto_libs=not no_auto_libs,
        rerun_cmd=rerun_cmd, rerun_cwd=rerun_cwd)


@cli.command("orc")
@click.pass_context
@click.argument("orcfile")
def orc(ctx,orcfile):
    """[Deprecated] Orchestrate cic"""
    orc = cic.OrcFile(orcfile)
    orc.run()


@cli.command("filter")
@click.pass_context
@click.argument("cicfile")
@click.argument("cell")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
def filter(ctx,cicfile,cell,includes):
    """[Deprecated] Parse a .cic file and optional included libraries"""
    load_design(cicfile, includes)


if __name__ == '__main__':
    cli(obj={})
