# Handoff — hierarchical stack routing on LELOTEMP_OTAR

State as of 2026-08-08. Everything below is measured, not assumed.

## Where the tree stands

| | |
|---|---|
| `LELOTEMP_OTAR` top | **0 DRC, 0 shorts, 16 opens** |
| `STACK_ROUTING` | `("r_deg",)` — p_sw deliberately OFF |
| cicpy tests | 38 pass |
| repos | cicpy + lelo_temp_sky130a committed, clean |

The 16 opens are work the group and top levels have not done yet, not
damage: all top-level signal routing was removed on purpose (power kept).

`r_deg` is the one stack routed at the top: `R1<0>` closes on **M1**,
drawn by route.py, `M1 || `.

## The one root cause behind most of today

**Geometry that is queued but not yet drawn is invisible to everything
that needs to see it.** Four separate failures were all this:

1. `route_stack_level` ran in `afterRoute` → the Route object was added,
   logged like a success, and `route()` was never called on it. Fixed by
   moving the call into `beforeRoute`.
2. `LELOTEMP_OTAR_P_SW.py` adds routes to a **parent** CellGroup at
   `afterPaint` — same thing, never drawn. That pycell's routing is now
   redundant with `route_stack_level` and should be deleted.
3. Per-net track maps inside a stack cannot see each other's routes,
   because none are drawn until the phase ends. Worked around by the
   caller remembering claimed trunks.
4. VCP's power strap is not drawn when a stack searches, so the ladder
   routes straight through it. **Still open** — see below.

## What was fixed and committed

- **Stack cells get their wires AND vias.** Route geometry is not in
  `layout.children`; it hangs off `Route` objects in `layout.routes`.
  The old walk found 32 rects in the whole parent. Vias are
  `InstanceCut` and were dropped by a "skip instances" filter.
  `P_SW` went from 5 copied rects to 35.
- **Bends.** `route_spec` emits `-|--` / `--|-` with `trunkx` taken from
  where the search found room.
- **Straight when the pins face each other.** The shape now comes from
  the PINS, not the path — a path bends for its own reasons (it must
  leave the pin-only layer to move). All five ladder links became plain
  `M1 ||`.
- **Trunk claims are a column AND a height**, rejected within one
  clearance in x and overlapping in y.
- **Pin layer inside a stack when it is FREE**, asked of
  `column_blockers`. NOT of `is_free`: the pin layer is pin-only, has no
  `ROUTE.directions` entry and therefore no tracks, so `is_free` returns
  False for every corridor on it — that mistake moved a clean `r_deg`
  off M1 for no reason.
- **Internal nets only** at stack level. A net with pins outside the
  stack belongs to the level above.
- **Supplies identified from the netlist** (a net on a device body
  terminal), not from a name list.

## p_sw — what is actually blocking it

### CORRECTION, 2026-08-08 later. The section below was wrong.

It said `route.py` ignores `trunkx` for a VERTICAL route and takes the
bar from the **union** of the net's own rects. Measured: `routeVertical`
uses `connection_center()`, which is the **overlap** of the two rects,
and the bars it drew landed at x `281700..284700` — correctly inside
net1's `275200..291200` overlap. `trunkx` is indeed ignored, and it
costs nothing. Both proposed next steps chase a non-problem.

**The real cause was the chain's placement order, not route.py.**

Every REYATR device in the column puts S at the bottom and D at the top.
A series chain therefore only abuts if it is stacked so the device below
offers D to the device above offering S. The order was the exact reverse
of that. Measured with the `blockers` tool, in the old order:

    net4  pins at y 436000  and  484000     48000 apart
    net3  pin  at y 444000   <- between them
    net2  pin  at y 476000   <- between them

Pins are 22400 wide in a column with 16000 of clear space, so **no
vertical existed at all** for net4 — nor for any other ladder net. The
router was right to fail; the geometry was impossible.

Reversed to `xbs6 xbs1 xbs2 xbs4 xbs7 xbs8` (read off the netlist:
VDD -xbs6- net1 -xbs1- net2 -xbs2- net4 -xbs4- net3 -xbs7- net5 -xbs8-
VCP) every ladder net becomes an abutting pair 28000 apart with nothing
between:

    net1  364000/368000  and  396000/400000
    net2  404000/408000  and  436000/440000
    net4  444000/448000  and  476000/480000
    net3  484000/488000  and  516000/520000
    net5  524000/528000  and  556000/560000

That alone took the top to **11 opens / 1 short**. The second half of
the fix, below, cleared the short.

### The second half: the pin layer was the wrong layer

The remaining short held `VDD_1V8, net1..net5`, and it was NOT the
trunks — those were clean pin-to-pin verticals at x 281700..284700.
Four bridges, all the same shape:

    net1|net2  M1 (268800,405000)-(272000,409000)
       touches M1 (268800,409000)-(272000,413000)

3200 × 4000 rects at the **far left** of the column, abutting in y,
`net=''`, parent `REYATR_PCH_4C1F2`. **Device-internal metal, not
routes.** The cell runs an unattributed M1 strip up its left side past
both S and D, and those two pins are 4000 apart in y and overlap in x.
A ladder link drawn on the PIN LAYER ties its device's D to its own S
through that strip.

Magic agreed, and more bluntly than cicpy did. Extracted:

    routed on M1:  Xxbs1 xbs8/S xbs8/G xbs8/S ...   D and S one node
    baseline:      Xxbs1 xbs1/D xbs8/G xbs1/S ...   distinct

All six ladder devices came out with D and S merged. cicpy's own check
saw it only after the flood relabelled the strip, because unattributed
metal is *tolerated* on the pin layer — it has to be, or no via could
land on a pin at all. That tolerance is the hole the ladder fell
through.

Fixed in `TrackMap.column_metal` + `_pin_layer_if_clear`: the pin layer
is chosen only when the corridor holds no foreign metal **attributed or
not**, tested over the PINS' full span rather than the trunk's — the
strip sits at the far left of a 22400 pin while the trunk is in the
middle of it. Two earlier attempts missed because the test ran in the
wrong place: `route_spec`'s "pins face each other" shortcut returned
before any layer check ran at all.

### State now

`STACK_ROUTING = ("r_deg", "p_sw")`, ladder on M2:

| | |
|---|---|
| `LELOTEMP_OTAR` | **0 DRC, 0 shorts, 11 opens** (was 16) |
| magic extraction | proper series chain, every device D ≠ S |
| `P_SW` stack cell | 25 routed rects (was 0) |
| cicpy tests | pass |

`R1<0>` moved from M1 to M2 as well — r_deg's column has unattributed
metal too. Two vias dearer and correct.

Still to do: `LELOTEMP_OTAR_P_SW.py` is **dead code**. Disabling its
`route()` changes nothing, which independently confirms its routes are
never drawn (it adds them to a parent CellGroup at stack-publication
time). Delete it.

The 11 remaining opens are group- and top-level work: `VDS VS VO VD1
VD2 VD3 VBP VCP VDD_1V8 PWRUP_1V8 PWRUP_N_1V8`.

### Also fixed since

`core/trackrouter.py` and `LayoutCell.addTrackRoute` are **deleted**.
Nothing called them; it was the prototype `mazerouter.py` replaced, and
it carried a hardcoded `M1/M2/M3/M4` cost table.

## p_sw LVS — a second, independent problem

`LELOTEMP_OTAR_P_SW` DRC is clean-ish (4 errors) but **LVS does not
match**, and the schematic side is the broken one:

```
Xxbs1 net6  net7  net8  net9  REYATR_PCH_4C1F2
Xxbs2 net10 net11 net12 net13 REYATR_PCH_4C1F2
```

Every pin gets its own auto-named net. The generated `.sch` has 6
symbols, 24 labels and 24 wires, but the labels/wires **do not touch the
symbol pins**, so xschem connects nothing and netgen merges six
identically-unconnected devices (`6->1`). "6 devices, 24 wires" looked
like success and was not. This is in `XschemPrinter`'s placement for
generated stack cells.

Also: `make stacksch` cannot produce these. Excluding cells to protect
the hand-drawn `LELOTEMP_OTAR.sch` also excludes the device cells the
symbol lookup needs, so the transpile dies on `REYATR_PCH_4C1F2`.
Unscoped, it dies on `REYATR_RES_36C2F0` (resistor symbol lookup, still
open). Workaround that works: transpile into a scratch dir with no
exclude and copy back the one file.

## Known incomplete

- `draw_supplies_first` draws **0**. Rings and straps do not arrive as
  `Route` objects on `layout.routes` — `addRouteRing` /
  `addPowerConnection` build geometry another way. Finding where that is
  queued is what makes "power first" real.
- `LELOTEMP_OTAR_P_SW.py` still adds a duplicate set of routes that are
  never drawn. Delete it.
- Router routes a net, not a set — no ordering or rip-up beyond the
  trunk claims.
