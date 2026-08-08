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

The ladder is 6 devices + filler in one 8.480 µm column, chain order
`xbs8 xbs7 xbs4 xbs2 xbs1 xbs6`, nets `net1..net5` internal.

Two facts that matter:

- The devices are `nf=2`: **source on both sides, drain in the middle.**
  Consecutive pins overlap in x by 16400 (net1: `275200..291200`), and
  that overlap is clear of VCP's strap at `300800..304000`. So a plain
  vertical is geometrically correct.
- **`route.py` ignores `trunkx` for a VERTICAL route.** It takes the bar
  from the union of the net's own rects — `268800..297600` for net1,
  wider than either pin — and that union reaches VCP and VDD_1V8. This
  is the immediate blocker: with p_sw enabled the top goes to 1 short
  holding `VCP, VDD_1V8, net1..net5`.

Next step is one of:
  a. make VERTICAL honour `trunkx` (or find the option that does), or
  b. pass route.py a narrowed rect per pin so its union IS the overlap.

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
