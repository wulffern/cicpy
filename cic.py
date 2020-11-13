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
sys.path.append(os.path.dirname(sys.argv[0]))
import cicpy as cic
import json


class cIcCreator:

    def __init__(self,schskill=True,layskill=True,spice=True,spectre=True,include=None,builddir=".",cic=None):
        self.schskill = schskill
        self.layskill = layskill
        self.spice = spice
        self.spectre = spectre
        self.include = include
        self.builddir = builddir
        self.cic = cic


    def readDesign(self,cicfile):
        self.design = cic.Design()
        self.design.fromJsonFile(cicfile)

    def readRules(self,techfile):
        self.rules = cic.Rules(techfile)

    


    def transpile(self,library):
        if(self.layskill):
            la = cic.SkillLayPrinter(library,self.rules)
            la.print(self.design)

        if(self.schskill):
            sc = cic.SkillSchPrinter(library,self.rules)
            sc.print(self.design)


        if(self.spice):
            print("WARNING: SPICE writing not implemented yet")
            pass

        if(self.spectre):
            print("WARNING: spectre writing not implemented yet")
            pass

    def run(self,jsonfile,techfile,library):
        
        cic_inc = ""
        if(len(self.include) > 0):
            cic_inc =" --I " +  " --I ".join(list(self.include))
        cic_cmd = f"{self.cic} --nogds {cic_inc} {jsonfile} {techfile} {library}"
        print("INFO: Running CIC")
        print(f"INFO: {cic_cmd}")
        os.system(f"cd {self.builddir}; {cic_cmd}")
        cicfile = f"{self.builddir}" + os.path.sep + os.path.basename(jsonfile.replace(".json",".cic"))
        self.cicfile =cicfile
        


@click.group()
@click.pass_context
@click.option("--include",multiple=True,help="Libraries to include")
@click.option("--layskill",is_flag=True,help="Write Skill Layout file")
@click.option("--schskill",is_flag=True,help="Write Skill Schematic file")
@click.option("--spice",is_flag=True,help="Write Spice file")
@click.option("--spectre",is_flag=True,help="Write Spectre file")
@click.option("--builddir",default=".",help="Directory to use for build")
@click.option("--cic",default="~/pro/cic/ciccreator/bin/linux/cic",help="Path to cIcCreator")
def cli(ctx,include,layskill,schskill,spice,spectre,builddir,cic):
    """ Python toolbox for Custom Integrated Circuit Creator (ciccreator). """

    ctx.ensure_object(dict)

    ctx.obj["cic"] = cIcCreator(include=include,
                       layskill=layskill,
                       schskill=schskill,
                       spice=spice,
                       spectre=spectre,
                       builddir = builddir,
                       cic=cic
    )
    pass

@cli.command("transpile")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("library")
def transpile(ctx,cicfile,techfile,library):
    """Translate .cic file into another file format (SKILL,SPECTRE,SPICE)"""
    c = ctx.obj["cic"]
    c.readDesign(cicfile)
    c.readRules(techfile)
    c.transpile(library)

@cli.command("jcell")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("cell")
@click.option("--child",default="",help="Show children")
def jcell(ctx,cicfile,techfile,cell,child):
    """Extract a cell from .cic """
    c = ctx.obj["cic"]
    c.readDesign(cicfile)
    c.readRules(techfile)
    if(cell in c.design.jcells):
        obj = c.design.jcells[cell]
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
        print("\n".join(c.design.cellnames))

    #c.readRules(techfile)
    #c.transpile(library)



    
            
@cli.command("cic")
@click.pass_context
@click.argument("jsonfile")
@click.argument("techfile")
@click.argument("library")
def run(ctx,jsonfile,techfile,library):
    c = ctx.obj["cic"]
    c.run(jsonfile,techfile,library)
    c.readDesign(c.cicfile)
    c.readRules(techfile)
    c.transpile(library)
    

if __name__ == '__main__':
    cli(obj={})

    
