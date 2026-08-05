# cicpy

`cicpy` is the Python frontend around ciccreator data and layout flows.

It can:
- translate `.cic` data into other formats
- generate Magic and Xschem output
- place stacks and devices
- generate SVG and other derived views

## Install latest and greatest

```bash
git clone https://github.com/wulffern/cicpy
cd cicpy
python3 -m pip install -e .
```

## Root workflow

The project now has root-level test and docs commands similar to `cicsim`.

```bash
make test
make docs
make build
```

## Docs

- [Layout flow](/cicpy/layout)
- [Routing examples](/cicpy/routes)
- [jcell test](/cicpy/jcell)
- [svg test](/cicpy/svg)
- [transpile test](/cicpy/transpile)
- [minecraft test](/cicpy/minecraft)
- [sch2mag test](/cicpy/sch2mag)

## Commands

- `transpile`: translate a `.cic` design into Magic, Xschem, SKILL, Verilog, and SPICE-family outputs. Supports extra library inputs through `--I`. See [transpile](/cicpy/transpile).
- `jcell`: extract one named cell from a `.cic` file as JSON. Supports extra library inputs through `--I`. See [jcell](/cicpy/jcell).
- `place` [Deprecated]: place devices from a `.cic` design using one of the built-in placement patterns. Supports extra library inputs through `--I`.
- `minecraft`: emit a Minecraft build script from one layout cell in a `.cic` design. Supports extra library inputs through `--I`. See [minecraft](/cicpy/minecraft).
- `svg`: render a `.cic` design library into SVG views. Supports extra library inputs through `--I`. See [svg](/cicpy/svg).
- `sch2mag`: read a schematic-driven project, place and route it, then write `.mag` and `.cic` layout output. See [sch2mag](/cicpy/sch2mag).
- `spi2mag`: read a SPICE subcircuit and placed-cell library, then write `.mag` and `.cic` layout output. This is the SPICE-driven counterpart to `sch2mag`.
- `orc` [Deprecated]: expand ORC recipes into grouped `.json` and `.spi` output files.
- `filter` [Deprecated]: currently a parse-only placeholder command that loads a `.cic` file, optionally merges included libraries through `--I`, and exits.

## Library Includes

Commands that read `.cic` data can load extra library files with `--I`.

```bash
cicpy svg top.cic tech/cic/sky130A.tech TOP \
  --I analog_lib.cic \
  --I digital_lib.cic
```

Use `--I` when the top-level `.cic` only contains one generated cell and references child cells stored in separate library `.cic` files.

For command help:

```bash
cicpy --help
cicpy <command> --help
```


# Custom IC Creator Python


# Why
This is a script package I use transpile from the output of ciccreator to other
formats.
 
# Changelog
| Version | Status             | Comment                                                    |
|:--------|:-------------------|:-----------------------------------------------------------|
| 0.0.1   | :white_check_mark: | First version of cicspy                                    |
| 0.1.5   | :white_check_mark: | First release to pypi                                      |
| 0.1.8   | :white_check_mark: | Added cicspi dependency and reorged to include subpackages |

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


