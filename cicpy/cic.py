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

import click
import os, sys
import cicpy as cic
import json

@click.group()
@click.pass_context
def cli(ctx):
    """ Python toolbox for Custom Integrated Circuit Creator (ciccreator). """
    ctx.ensure_object(dict)
    pass

@cli.command("transpile")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("library")
@click.option("--layskill",is_flag=True,help="Write Skill Layout file")
@click.option("--schskill",is_flag=True,help="Write Skill Schematic file")
@click.option("--winfo",is_flag=True,help="Write Info file")
@click.option("--rinfo",default="",help="Read Info file")
@click.option("--verilog",is_flag=True,help="Write verilog file")
@click.option("--smash",default=None,help="List of transistors to smash schematic hierarchy")
def transpile(ctx,cicfile,techfile,library,layskill,schskill,winfo,rinfo,verilog,smash):
    """Translate .cic file into another file format (SKILL,SPECTRE,SPICE)"""

    design = cic.Design()
    design.fromJsonFile(cicfile)
    rules = cic.Rules(techfile)

    if(layskill):
        la = cic.SkillLayPrinter(library,rules)
        la.print(design)

    if(schskill):
        sc = cic.SkillSchPrinter(library,rules,smash)
        sc.print(design)

    if(winfo):
        obj = cic.CellInfoPrinter(library,rules)
        obj.print(design)

    if(verilog):
        obj = cic.VerilogPrinter(library,rules)
        obj.print(design)


@cli.command("jcell")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--child",default="",help="Show children")
def jcell(ctx,cicfile,techfile,cell,child):
    """Extract a cell from .cic """

    design = cic.Design()
    design.fromJsonFile(cicfile)
    rules = cic.Rules(techfile)

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
def place(ctx,cicfile,techfile,layoutfile,circuit,pattern):
    """Place a bunc of transistors according to pattern"""

    design = cic.Design()
    design.fromJsonFile(cicfile)
    rules = cic.Rules(techfile)

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
def minecraft(ctx,cicfile,techfile,cell,child,x,y):
    """Make a mincraft script *.mc from *.cic """

    design = cic.Design()
    design.fromJsonFile(cicfile)
    rules = cic.Rules(techfile)
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


def my_main():
    cli(obj={})

if __name__ == '__main__':
    my_main()