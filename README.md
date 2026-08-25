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
| `compile` | Compile a ciccreator object definition (`.json`) into a `.cic` — the job `bin/cic` does |
| `svg` | Generate SVG views from a `.cic` library |
| `gui` | Open a Qt viewer on a `.cic` file (needs `pip install cicpy[gui]`) |
| `checkroutes` | Check a cell for shorts and opens |
| `tracks` | Report which routing tracks are occupied, and by what |
| `blockers` | What stops a net from dropping a via column in a box |
| `findroute` | Search a path for a net and report it without drawing anything |
| `stackorder` | Which columns are interleaved, and what reordering them would cost |
| `cost` | What a cell's routing costs: wire length, vias, pieces |
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

### Compiling and transpiling in one pass

`compile` accepts the same output flags as `transpile` and runs them on the
design it just built, so there is no write-then-reload round trip:

```sh
cicpy compile --I cic cic/ip.json cic/sky130.tech MYLIB --spice --xschem --magic
```

This writes `MYLIB.cic` and the outputs together. The result is byte-identical
to running `compile` and then `transpile` over the file it wrote.

### Where output goes

Diagnostics go through the standard `logging` machinery, rendered with
[rich](https://rich.readthedocs.io) — level, logger name, and colour. Data a
command was asked for (reports, listings, netlists) goes to the console object
on stdout, so it stays pipeable. `cicpy-mcp` logs on stderr, keeping stdout a
clean protocol channel. Nothing in the package prints directly.

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
| 0.3.1 | `compile` gained the transpile outputs, running them from memory; the spice banner no longer names the Python class |
| 0.3.0 | rich is the default terminal output: one logger module, a console for data, no bare `print()` |
| 0.2.0 | Declarative routing: `paths`/`blocked` on sidecar cells, anchored stories with no coordinates, the search emits paste-ready path entries, stacked supply rings, trustworthy checkroutes, MCP server |
