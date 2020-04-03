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



@click.group()
@click.pass_context
def cli(ctx):
    """ Python toolbox for Custom Integrated Circuit Creator (ciccreator). """
    pass

@cli.command("transpose")
@click.pass_context
@click.argument("cicfile")
@click.argument("techfile")
@click.argument("library")
@click.option("--layskill",is_flag=True,help="Output Skill Layout file")
@click.option("--schskill",is_flag=True,help="Output Skill Schematic file")
@click.option("--spice",is_flag=True,help="Output Spice file")
@click.option("--spectre",is_flag=True,help="Output Spectre file")
def transpose(ctx,cicfile,techfile,library,layskill,schskill,spice,spectre):
    """Translate .cic file into another file format """
    d = cic.Design()
    d.fromJsonFile(cicfile)
    r = cic.Rules(techfile)
    
    if(layskill):
        la = cic.SkillLayPrinter(library,r)
        la.print(d)

    if(schskill):
        sc = cic.SkillSchPrinter(library,r)
        sc.print(d)
        pass

    if(spice):
        pass
            


if __name__ == '__main__':
    cli(obj={})

    
