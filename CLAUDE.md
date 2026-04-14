# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
