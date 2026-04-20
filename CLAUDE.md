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

## What cicpy Does

`cicpy` is the Python frontend for **ciccreator** — it translates `.cic` (JSON-based) IC design files into layout and schematic formats (SKILL, SPICE, Verilog, Xschem, Magic). The main use case is automated place-and-route: `spi2mag`/`sch2mag` take a SPICE netlist and generate a Magic layout file.

## Install

```bash
pip install -e .
```

Entry point: `cicpy` CLI → `cicpy.cic:cli`

## Commands

```bash
# Run all integration tests
make test

# Run a single test suite
cd tests/spi2mag && make test

# Lint
ruff check src/

# Build distribution
make build
```

There are no Python unittest files — all tests are Makefile-driven integration tests that invoke the `cicpy` CLI and check output files exist.

Each test subdirectory under `tests/` corresponds to a CLI command: `transpile`, `jcell`, `place`, `svg`, `spi2mag`, `sch2mag`, `routes`, `orc`, `filter`, `minecraft`.

## Architecture

### Source layout

```
src/cicpy/
  cic.py          — Click CLI entry point (9 commands)
  core/           — Data model
  printer/        — Output generators
  eda/            — EDA tool integrations (Magic, Xschem)
  place/          — Placement algorithms
  orc/            — Orchestration (deprecated)
```

### Core data model (`core/`)

- `Design` — top-level container; loaded from one or more `.cic` JSON files
- `Cell` / `LayoutCell` — a single circuit cell; `LayoutCell` adds placement/routing state
- `CellGroup` — groups of instances used during placement
- `Instance` — a placed cell reference
- `Rect`, `Port`, `Route`, `Layer`, `Rules` — geometry and technology primitives
- `Graph` — connectivity graph used for routing and DRC checks
- `Rules` — singleton loaded from a `.tech` file; controls spacing, layers, etc.

### Printers (`printer/`)

Each printer takes a `Design` and writes output files:
- `SkillLayPrinter` / `SkillSchPrinter` → Virtuoso SKILL layout/schematic (`.il`)
- `SpicePrinter` → `.spice` (ngspice) and `.spi` (CDL)
- `XschemPrinter` → Xschem schematics
- `MagicPrinter` → Magic layout (`.mag`)
- `VerilogPrinter` → `.v`
- `SvgPrinter` → SVG visualization HTML
- `MinecraftCellPrinter` → Minecraft script (novelty)

### EDA integrations (`eda/`)

- `MagicDesign` — extends `Design`; scans a library directory for `.mag` files, reads a SPICE netlist via `cicspi`, creates a `LayoutCell`, runs place-and-route, then writes output with `MagicPrinter`
- `CellFactory` — instantiates layout cells from parsed SPICE subcircuits
- `Xschem` — runs Xschem to netlist a `.sch` before calling `spi2mag`

### spi2mag / sch2mag flow

1. Parse SPICE → build `LayoutCell` with instances
2. Load pycell hook if `<libdir>/<lib>/<CELL>.py` exists (dynamically imported)
3. Call `lcell.layout(pycell, pycellData)` — runs placement, routing, cuts
4. Optionally run connectivity checks (`--check-connectivity`)
5. Write `.mag` and `.cic` via `MagicPrinter`

### Pycell hooks

Pycell files (`py/<CELL>.py` in an IP repo) are Python modules that customize layout. They are dynamically imported by `spi2mag`. A pycell module may define a `data` dict and hook functions called by `LayoutCell.layout()`:

```
beforePlace, afterPlace, beforeRoute, afterRoute, beforePaint, afterPaint
```

### Technology files

`.tech` files live in `../tech/cic/<techlib>.tech` relative to the working directory. `Rules` is a singleton — call `Rules.getInstance()` after construction to access it from core objects.

