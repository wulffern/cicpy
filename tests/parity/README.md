# Parity with ciccreator

cicpy can only replace ciccreator if it compiles the same object files
into the same layout. This directory is how that claim gets checked
rather than asserted.

## Measuring

```sh
# reference
git clone https://github.com/wulffern/ciccreator
cd ciccreator && make                     # needs Qt6 (qt6-base-dev)
bin/cic examples/routes.json examples/tech.json routes

# candidate
cicpy compile examples/routes.json examples/tech.json cicpy_routes

# compare
python3 tests/parity/compare_cic.py routes.cic cicpy_routes.cic
```

`compare_cic.py` compares GEOMETRY, not bytes: the two writers disagree
on bookkeeping keys (cicpy emits `ckt`, ciccreator emits `libcell`,
`meta`, `physicalOnly`) and no such difference moves a rectangle. It
reports cells missing, cells extra, and per-cell shape differences,
then a single parity percentage.

## Where the port stands

The compiler front end -- `cicpy compile`, in `src/cicpy/compiler/` --
is complete: it reads object files the way ciccreator does, resolves
`inherit`/`leech` chains, dispatches JSON keys onto cell methods by
reflection, and runs the full
afterNew/place/route/addAllPorts/paint lifecycle.

What is NOT ported is `PatternTile.paint()`
(cic-core/src/core/patterntile.cpp:348, ~280 lines plus
`findPatternRects` and `paintEnclosures`). PatternTile is a leaf cell
that nearly every other cell places, so until it lands, `cicpy compile`
builds the hierarchy and then has no geometry to put in it. It raises
`NotPortedYet` rather than emitting an empty cell, because an empty
cell scores as a shape count of zero here and would read as progress.

Run with `--keep-going` to compile past it and see how far the rest gets.
