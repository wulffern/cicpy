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
import os, sys
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
def xsch2mag(ctx,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity):
    """Netlist a xschem to spice, and load file to Magic"""

    os.system(f"make xsch LIB={lib} CELL={cell}")

    spi = "xsch/" + cell + ".spice"

    _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity)



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
def spi2mag(ctx,spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity):
    """Translate a SPICE file to Magic"""
    _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity)



def _spi2mag(spi,lib,cell,libdir,techlib,xspace,yspace,gbreak,check_connectivity=False):

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

    pycell = None
    pycellData = None
    if(os.path.exists(lcell.dirname + lcell.name + ".py")):
        sys.path.append(lcell.dirname)
        pycell = importlib.import_module(lcell.name)
        if(hasattr(pycell,"data")):
            pycellData = pycell.data

    lcell.layout(pycell,pycellData)

    if check_connectivity:
        _report_route_shorts(lcell)
        _report_connectivity(lcell)

    #- Add cuts after the layout has been routed
    design.addCuts()

    obj = cic.MagicPrinter(libdir + lib,rules)
    obj.print(design)
    #for m in design.maglib.values():
        #if(m._lay is not None):

    with open(libdir + lib + os.path.sep + lcell.name + ".cic","w") as fo:
        fo.write(json.dumps(design.toJson(),indent=4))
        #fo.write(json.dumps(design.maglib["JNWTR_RPPO2"]._lay.toJson(),indent=4))


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

    for open_net in opens:
        if open_net["type"] == "split":
            log.warning(f"OPEN net={open_net['net']} split_components={open_net['components']}")
        else:
            log.warning(f"OPEN net={open_net['net']} unmatched_anchors={open_net['anchors']}")





@cli.command("gui")
@click.pass_context
@click.argument("cicfile")
@click.option("--tech","techfile",default=None,help="Tech file (.tech). Auto-discovered from <ipdir>/tech/cic/*.tech if omitted.")
@click.option("--I","includes",multiple=True,help="Additional .cic library file or glob to merge before processing")
@click.option("--no-auto-libs",is_flag=True,help="Disable auto-discovery of dependency libraries via the IP's config.yaml.")
def gui(ctx,cicfile,techfile,includes,no_auto_libs):
    """Open a Qt viewer on a .cic file (PySide6 required: pip install 'cicpy[gui]')."""
    from cicpy.gui.app import run
    run(cicfile, techfile=techfile, includes=includes, auto_libs=not no_auto_libs)


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
