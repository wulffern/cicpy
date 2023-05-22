
# Custom IC Creator Python


# Why
This is a script package I use transpile from the output of ciccreator to other
formats.
 
# Changelog
| Version | Status | Comment |
|:--|:--|:--|
|0.0.1| :white_check_mark: | First version of cicspy|
|0.1.5| :white_check_mark: | First release to pypi|

# Install this module
If you want to follow the latest and greatest
``` sh
git clone https://github.com/wulffern/cicpy
cd cicpy
python3 -m pip install  -e . 
```

If you want something that does not change that often
``` sh
python3 -m pip install cicpy 

```

# Commands

For the latest help, check `cicpy --help`, and `cicpy <command> --help`

``` sh
Usage: cicpy [OPTIONS] COMMAND [ARGS]...

  Python toolbox for Custom Integrated Circuit Creator (ciccreator).

Options:
  --help  Show this message and exit.

Commands:
  jcell      Extract a cell from .cic
  minecraft  Make a mincraft script *.mc from *.cic
  place      Place a bunch of transistors according to pattern
  svg        Make an SVG
  transpile  Translate .cic file into another file format...
```

``` sh
Usage: cicpy transpile [OPTIONS] CICFILE TECHFILE LIBRARY

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
