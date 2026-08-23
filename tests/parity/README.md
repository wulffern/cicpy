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

`cicpy compile examples/routes.json examples/tech.json` runs end to end
and reaches **8 of 46 cells matching ciccreator exactly (17.4%)**,
including every PatternTile leaf.

PatternTile is ported: the character grid, the sub patterns from the
file's `patterns` map, contacts and contact pairs, port characters,
the merge with the neighbour on the left, and enclosures. The leaf
cells it draws -- DDD, DDA, DDMVIA and the rest -- match the reference
shape for shape.

What is left is one coherent thing: HOW A CELL PUBLISHES ITS PORTS.
Against the reference, each remaining cell shows

    want 2x Port  M1 ... 'B'      +  1x Text TXT ... 'XA1'
    got  1x InstancePort M1 ... 'B'

so three symptoms of the same gap -- ciccreator publishes a `Port` on
the parent through `updatePort`, emits a `Text` label per instance,
and resolves `XA1:S` style names in route commands
(`findAllRectangles`) that currently find nothing. Fixing that is the
next chunk, and it should close most of the remaining 38 cells at once.

The SAR example needs more than this: it adds LayoutDigitalCell's row
conventions, LayoutSARCDAC, LayoutCapCellSmall and the Gds pattern
devices, none of which are ported.
