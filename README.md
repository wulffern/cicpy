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
