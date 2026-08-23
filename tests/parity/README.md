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

**routes.json: 45/46 cells (97.8%).** The one holdout is TEST_R, off by
one database unit -- ciccreator's integer rotate(90) drops one, a bug
in the reference that cicpy does not replicate.

**SAR_ESSCIRC16_28N: 50/52 cells (96.2%), 4832 of 4877 shapes (99.1%).**
Every leaf, every standard cell, both CDAC columns and the unrouted top
match exactly. The one differing cell is the routed top SAR9B_EV,
where two of its own nets disagree in detail: the EN spine resolves
its nested XA0:XA1:XA5:EN pins 150 units to the right of the
reference, and the AVSS edge straps end one cut height short of the
reference's ring bar. (SAR9B_EV_NOROUTE, same placement without the
top routes, matches exactly.)

Flow-level behaviour the two tools legitimately disagree on is
selected by `Route.compat` -- the compiler sets "ciccreator" for the
duration of a compile; spi2mag keeps cicpy's own conventions
(landing rects, cut fitting, group spacing and ordering, power sheet
layer, box semantics).
