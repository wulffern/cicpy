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
@click.option("--spicefile", default="", help="Spice file")
@click.option("--subckt", default="", help="Subcircuit name")
@click.option("--oformat",default="spectre",help="spectre|aimspice")
def makesim(cfgfile,spicefile,subckt,oformat):
    sc = cicpy.SimConf(subckt)
    sc.fromFile(cfgfile)

    if(oformat == "spectre"):
        ss = cicpy.SpectreWriter(sc)
        ss.write(spicefile,subckt,cfgfile)


if __name__ == "__main__":
    cli()
