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

**routes.json: 45 of 46 cells match ciccreator exactly (97.8%), 766
shapes on each side.**

The one remaining cell is TEST_R, off by exactly one database unit:
ciccreator's integer Rect::rotate(90) loses a unit (a 6300-wide cell
comes back 6299 wide, ports at 151 instead of 150). That is a bug in
the reference, not a gap in the port, and cicpy does not replicate it.

Behaviour the two flows legitimately disagree on is selected by
`Route.compat` -- the compiler sets "ciccreator" for the duration of a
compile, spi2mag keeps cicpy's own conventions:

  - the landing rect keeps the pin when a cut straddles its centre
    (cicpy follows the cut, measured against VR1's trunk)
  - no cut re-alignment to the wire, no fitting chain
  - routeVertical is one wire, bound edge to bound edge
  - instances abut (no CELL-space gap between groups)

The SAR example is the next target: LayoutDigitalCell's row
conventions, PatternResistor, the Gds pattern devices, LayoutSARCDAC
and the capacitor cells are not yet ported.
