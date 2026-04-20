# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**cicpy** is a Python package that transpiles Custom IC Creator (`.cic`) design files into multiple EDA tool formats. It reads gzip-compressed JSON design files and outputs SKILL layout/schematic, SPICE netlists, Verilog, Xschem schematics, Magic layout, and SVG.

## Commands

### Development setup
```sh
pip install -e .
```

### Run all tests
```sh
make test
```

Tests are CLI-based integration tests — each subdirectory under `tests/` has its own `Makefile` with a `test` target that invokes the `cicpy` CLI against real design files. There are no unit tests (`make unit_test` is a no-op).

### Run a single test suite
```sh
cd tests/transpile && make test
cd tests/sch2mag && make test
cd tests/spi2mag && make test
```

### Build and publish
```sh
make build
make test_upload   # testpypi
make upload        # pypi (requires token)
```

## Architecture

### Data flow
1. `.cic.gz` files (gzip JSON from ciccreator) are loaded via `Design.fromJsonFiles()`
2. A `Rules` object is loaded from a `.tech` file (YAML-based technology rules)
3. The `Design` + `Rules` are passed to a printer, which generates the output

### Key abstractions

**`core/`** — IC design data model:
- `Design` — container for all cells; loads/merges multiple `.cic` files
- `Cell` / `LayoutCell` — individual circuit cells with ports, instances, rectangles, routes
- `Instance` — instantiation of one cell inside another
- `Port` / `InstancePort` — electrical ports and their mappings
- `Rect` — geometric rectangle primitive (coordinates in technology units)
- `Route` / `Routering` — electrical net routing, connectivity graph algorithms
- `Rules` — technology rules parsed from `.tech` YAML files
- `Cut` / `InstanceCut` — via/contact definitions between layers

**`printer/`** — output format generators, all extending `DesignPrinter`:
- `SkillLayPrinter` / `SkillSchPrinter` — Cadence SKILL layout and schematic
- `SpicePrinter` — ngspice `.spice` and CDL `.spi` netlists
- `XschemPrinter` — Xschem schematic symbols and schematics
- `MagicPrinter` — Magic layout `.mag` files
- `VerilogPrinter` — Verilog HDL
- `SvgPrinter` — SVG visualization

**`eda/`** — EDA tool interfaces for reading existing layouts:
- `MagicDesign` / `Magic` — scan existing Magic cell libraries, read `.mag` files
- `Xschem` — parse Xschem schematic files

**`place/`** — transistor placement algorithms (diffpair, horizontal, vertical)

### CLI entry point

`src/cicpy/cic.py` defines all Click commands. The `cli` group is registered as `cicpy` in `pyproject.toml`. All commands follow the pattern: load `Rules`, load `Design`, instantiate a printer, call `printer.print(design)`.

### `spi2mag` / `sch2mag` workflow

These commands handle the reverse direction — reading a SPICE netlist and placing existing Magic cells:
1. `MagicDesign.scanLibraryPath()` discovers available Magic cells
2. `design.readFromSpice()` parses the netlist into a `LayoutCell`
3. `lcell.layout()` performs placement and routing
4. Optional per-cell `.py` customization files are dynamically imported from the library directory
5. `MagicPrinter` writes the result; a `.cic` JSON dump is also written

### Technology files

`.tech` files (YAML) define layers, spacing rules, and via definitions. They live at `../tech/cic/<techlib>.tech` relative to the working directory for `spi2mag`/`sch2mag`. The `transpile` tests use `tests/transpile/demo.tech`.

### Test design files

The primary test design is `tests/transpile/SAR9B_CV.cic.gz` (a SAR ADC). Most test Makefiles reference this file via relative paths.
