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

Beyond ciccreator's own examples, the harness runs against the real IP
repositories the reference compiles today -- each repo's `cic/ip.json`
built by both tools on the same inputs (`bin/cic --I cic cic/ip.json
cic/<tech>.tech LIB` from the repo's work directory):

| design                    | parity            |
|---------------------------|-------------------|
| jnw_tr_sky130a            | 37/37 cells, 100% |
| jnw_atr_sky130a           | 52/52 cells, 100% |
| rey_tr_sky130a            | 39/39 cells, 100% |
| rey_atr_sky130a           | 210/210 cells, 100% |
| lelo_atr_sky130a          | 62/62 cells, 100% |
| lelo_tr_ihp13g2           | 44/44 cells, 100% |
| lelo_atr_ihp13g2          | 52/52 cells, 100% |
| cnr_atr_sky130nm          | 44/44 cells, 100% |
| sun_tr_sky130nm           | 67/68 cells       |
| sun_sar9b_sky130nm        | 51/54 cells       |
| sun_pll_sky130nm          | 35/43 cells       |
| routes.json (examples)    | 45/46 cells       |
| SAR_ESSCIRC16_28N         | 51/52 cells       |

**routes.json: 45/46.** The one holdout is TEST_R, off by one database
unit -- ciccreator's integer rotate(90) drops one, a bug in the
reference that cicpy does not replicate.

**SAR_ESSCIRC16_28N: 51/52.** The one differing cell is the routed top
SAR9B_EV, whose EN spine places its via cuts off the reference by one
pin-width-vs-via-width margin -- the same signature as the sun_sar9b
SAR8B/SAR9B tops, still being chased.

**sun_tr 67/68**: the ring-heavy RG12TRIX1_CV. **sun_pll 35/43**: cut
row centring and ring trims in cells consuming the TR library.

Flow-level behaviour the two tools legitimately disagree on is
selected by `Route.compat` -- the compiler sets "ciccreator" for the
duration of a compile; spi2mag keeps cicpy's own conventions
(landing rects, cut fitting, group spacing and ordering, power sheet
layer, box semantics).
