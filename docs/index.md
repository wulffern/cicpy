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

Python toolbox for transpiling [ciccreator](https://github.com/wulffern/ciccreator) output to other IC design formats.

## Install

Latest from git:
```sh
git clone https://github.com/wulffern/cicpy
cd cicpy
pip install -e .
```

Stable release from PyPI:
```sh
pip install cicpy
```

## Commands

```
cicpy [OPTIONS] COMMAND [ARGS]...
```

| Command | Description |
|---------|-------------|
| `transpile` | Translate `.cic` to SKILL layout/schematic, SPICE, Verilog, Xschem, Magic, SVG |
| `jcell` | Extract a single cell from a `.cic` file as JSON |
| `sch2mag` | Netlist an Xschem schematic to SPICE, then place and route to Magic |
| `spi2mag` | Place and route a SPICE subcircuit to Magic |
| `svg` | Generate SVG views from a `.cic` library |
| `minecraft` | Emit a Minecraft build script from a layout cell |
| `place` | *(Deprecated)* Place transistors by pattern |
| `orc` | *(Deprecated)* Orchestration runner |
| `filter` | *(Deprecated)* Parse-only placeholder |

For full option lists: `cicpy --help` and `cicpy <command> --help`

### Common `transpile` options

```sh
cicpy transpile SAR9B.cic.gz demo.tech SAR9B \
  --layskill    # Cadence SKILL layout
  --schskill    # Cadence SKILL schematic
  --spice       # ngspice + CDL netlists
  --xschem      # Xschem schematics
  --magic       # Magic .mag layout
  --verilog     # Verilog (experimental)
```

### Extra library includes

Commands that read `.cic` data accept multiple `--I` flags to merge library cells:

```sh
cicpy svg top.cic tech/cic/sky130A.tech TOP \
  --I analog_lib.cic \
  --I digital_lib.cic
```

## Changelog

| Version | Comment |
|---------|---------|
| 0.0.1 | First version |
| 0.1.5 | First PyPI release |
| 0.1.8 | Added cicspi dependency and subpackages |
| 0.1.9 | Routing, Magic layout, and connectivity improvements |


