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

For an IP repository the invocation is the one its Makefile uses:

```sh
cd <repo>/work
../../ciccreator/bin/cic --I ../cic ../cic/ip.json ../cic/sky130.tech ref_LIB
cicpy compile --I ../cic ../cic/ip.json ../cic/sky130.tech cicpy_LIB
python3 tests/parity/compare_cic.py ref_LIB.cic cicpy_LIB.cic
```

`compare_cic.py` compares GEOMETRY, not bytes: the two writers disagree
on bookkeeping keys (cicpy emits `ckt`, ciccreator emits `libcell`,
`meta`, `physicalOnly`) and no such difference moves a rectangle. It
reports cells missing, cells extra, and per-cell shape differences,
then a single parity percentage.

## Where the port stands

Every real design compiles geometry-exact:

| design | parity |
|---|---|
| SAR_ESSCIRC16_28N | 52/52 |
| jnw_tr_sky130a | 37/37 |
| jnw_atr_sky130a | 52/52 |
| rey_tr_sky130a | 39/39 |
| rey_atr_sky130a | 210/210 |
| lelo_atr_sky130a | 62/62 |
| lelo_tr_ihp13g2 | 44/44 |
| lelo_atr_ihp13g2 | 52/52 |
| cnr_atr_sky130nm | 44/44 |
| sun_tr_sky130nm | 68/68 |
| sun_sar9b_sky130nm | 54/54 |
| sun_pll_sky130nm | 43/43 |

**routes.json: 45/46.** The one holdout is TEST_R, off by one database
unit -- ciccreator's integer rotate(90) drops one, a bug in the
reference that cicpy does not replicate.

## What the reference actually does

Reaching exact parity meant treating the binary's behaviour -- quirks
included -- as the spec. The load-bearing ones, so nobody re-derives
them:

- Hook dicts run ALPHABETICALLY (`QJsonObject::keys()` is sorted).
- `alternateGroup(QJsonValue)` and `noPowerRoute(QJsonValue)` ignore
  the value and set their flag TRUE: `"alternateGroup": 0` mirrors,
  `"noPowerRoute": 0` disables the power sheet.
- One global subckt registry; a netlist parsed later overwrites a
  library's subckt (node order included).
- Box unions recompute at every add over the children's CURRENT
  boxes; a queued route counts as (0,0,0,0) until it draws, and
  whether that zero survives depends on whether anything is added
  afterwards. `boundaryIgnoreRouting` defaults TRUE on a LayoutCell
  (box = non-cut instances only) and round-trips through .cic files.
- An instance's ports are a name-keyed map: on a net landing on two
  pins of one instance, the LAST pin's rect answers.
- `addRouteRing` expands `Y<11:0>` to a ring per bit, high to low.

Flow-level behaviour the two tools legitimately disagree on is
selected by `Route.compat` -- the compiler sets "ciccreator" for the
duration of a compile; spi2mag keeps cicpy's own conventions.
