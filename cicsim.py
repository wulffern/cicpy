import json
import click
import sys
import re
import os
import difflib
import cicpy
sys.path.append(os.path.dirname(sys.argv[0]))



@click.group()
def cli():
    pass

@cli.command()
@click.option("--spicefile", default="", help="Spice file")
@click.option("--subckt", default="", help="Subcircuit name")
def makeconf(spicefile,subckt):
    sp = cicpy.SpiceParser()
    ports = sp.fastGetPortsFromFile(spicefile,subckt)
    sc = cicpy.getSimConf(subckt,ports)
    sc.toFile("tmp_sim.cfg")

@cli.command()
@click.option("--cfgfile", default="", help="Config file")
@click.option("--include", default="", help="Simulation include file")
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=False, help="Run simulator")
def makesim(cfgfile,include,oformat,run):
    sc = cicpy.SimConf()
    sc.fromFile(cfgfile)

    if(oformat == "spectre"):
        ss = cicpy.SpectreWriter(sc)
        ss.write(include,cfgfile)

if __name__ == "__main__":
    cli()
