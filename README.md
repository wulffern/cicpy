
# Custom IC Creator Python


# Why
This is a script package I use transpile from the output of ciccreator to other
formats, like
- Netlist from cadence
- Run corner simulations
- Run ocean scripts on spectre results
- Run python scripts to combine ocean results
- Combine results

 
# Changelog
| Version | Status | Comment |
|:--|:--|:--|
|0.0.1| :white_check_mark: | First version of cicspy|

# Install this module
If you want to follow the latest and greatest
``` sh
mkdir pro
cd pro
git clone https://github.com/wulffern/cicpy
cd cicpy
python3 -m pip install  -e . 

```

# Commands

``` sh
Usage: cic.py [OPTIONS] COMMAND [ARGS]...

  Python toolbox for Custom Integrated Circuit Creator (ciccreator).

Options:
  --help  Show this message and exit.

Commands:
  jcell      Extract a cell from .cic
  minecraft  Make a mincraft script *.mc from *.cic
  place      Place a bunch of transistors according to pattern
  svg        Make an SVG
  transpile  Translate .cic file into another file format..
```


``` sh
python3 cicpy/cic.py transpile --help
Usage: cic.py transpile [OPTIONS] CICFILE TECHFILE LIBRARY

  Translate .cic file into another file format (SKILL,SPECTRE,SPICE)

Options:
  --layskill      Write Skill Layout file
  --schskill      Write Skill Schematic file
  --winfo         Write Info file [ALPHA]
  --rinfo TEXT    Read Info file [ALPHA]
  --verilog       Write verilog file [EXPERIMENTAL]
  --spice         Write spice file
  --xschem        Write xschem schematics
  --magic         Write magic layout
  --smash TEXT    List of transistors to smash schematic hierarchy
  --exclude TEXT  Regex of cells to ignore
  --help          Show this message and exit.
```
