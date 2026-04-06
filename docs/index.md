# cicpy

`cicpy` is the Python frontend around ciccreator data and layout flows.

It can:
- translate `.cic` data into other formats
- generate Magic and Xschem output
- place stacks and devices
- generate SVG and other derived views

## Install

```bash
git clone https://github.com/wulffern/cicpy
cd cicpy
pip install -e .
```

## Commands

```bash
make test
make docs
make build
```

| Command | Description |
|---------|-------------|
| `transpile` | Translate `.cic` to SKILL layout/schematic, SPICE, Verilog, Xschem, Magic. See [transpile](/cicpy/transpile). |
| `jcell` | Extract one named cell from a `.cic` file as JSON. See [jcell](/cicpy/jcell). |
| `sch2mag` | Netlist an Xschem schematic, then place and route to Magic. See [sch2mag](/cicpy/sch2mag). |
| `spi2mag` | Place and route a SPICE subcircuit to Magic. SPICE-driven counterpart to `sch2mag`. |
| `svg` | Render a `.cic` library into SVG views. See [svg](/cicpy/svg). |
| `minecraft` | Emit a Minecraft build script from a layout cell. See [minecraft](/cicpy/minecraft). |
| `place` | *(Deprecated)* Place devices by pattern. |
| `orc` | *(Deprecated)* Orchestration runner. |
| `filter` | *(Deprecated)* Parse-only placeholder. |

Use `--I` to merge additional `.cic` library files into any command that reads `.cic` data:

```bash
cicpy svg top.cic tech/cic/sky130A.tech TOP \
  --I analog_lib.cic \
  --I digital_lib.cic
```

For option details: `cicpy --help` and `cicpy <command> --help`

## Docs

- [Layout flow](/cicpy/layout)
- [Custom pycell API](/cicpy/pycell)
- [Routing examples](/cicpy/routes)
- [jcell test](/cicpy/jcell)
- [svg test](/cicpy/svg)
- [transpile test](/cicpy/transpile)
- [minecraft test](/cicpy/minecraft)
- [sch2mag test](/cicpy/sch2mag)
