# Stacks as cells: generate once, instantiate in the top

Goal: stop laying out a big analog cell as one flat field of devices.
Generate each stack as a real cell -- its own `.mag`, `.sch`, `.sym`,
its own DRC and LVS -- and have the top instantiate those cells and
route only between their ports.

Everything below is measured on 2026-08-08, on a 70-device OTA
(`LELOTEMP_OTAR`, 8 stacks). Numbers are from the tools, not estimates.

## Where it already works

The generation machinery is done and verified:

| step | state |
|---|---|
| `plan_stack_cells` — names, instances, ports, internal nets | works |
| `run_stack_pycells` — a stack's own `<CELL>.py route(layout, entry)` | works, runs between afterPlace and beforeRoute |
| `route_stack_level` — search-based routing per stack | works |
| `write_stack_cells` — publishes each stack as a cell, writes `.mag` | works |
| `stack_subckt` — the generated subckt | works |
| `make stacksch` — writes `.sch` and `.sym` per stack | **now works** |
| **standalone DRC of every generated stack cell** | **all 8 clean** |

`make stacksch` and the schematics were broken until today by two bugs
in `XschemPrinter`, both now fixed (cicpy 474cdb2): the printer never
looked for symbols in the library it was writing, and a symbol read and
written back grew a duplicate `K` block every run. Before the fix the
generated stack schematic put every wire on a placeholder pin grid
touching nothing, xschem connected nothing, and netgen merged six
identical devices into one — which reads as "6 devices, 24 wires" and
looks like success.

So a stack cell can be generated and is DRC clean. What it cannot yet
do is pass **LVS**, and that is the whole gate.

## The one thing in the way

**A stack cell must join every net it has two or more pins of** —
boundary nets included. A net with pins outside becomes a port; a cell
that leaves its internal pins apart presents the same net at several
ports and hands the parent a problem it just invented.

`route_stack_level(boundary=True)` does this. It is implemented and
**off by default**. Measured per stack, one at a time:

| stack | boundary nets routed | shorts |
|---|---|---|
| `r_deg` | 2 | **0** |
| `p_in_a` | 4 | **0** |
| `p_in_b` | 4 | **0** |
| `p_sw` | 2 | 1 |
| `p_bias` | 4 | 1 |
| `n_load_a` | 2 | 1 |
| `n_load_b` | 2 | 1 |
| `n_mirr` | 3 | 1 |

Three of eight are cell-ready today. **All five failures are the same
cause**, and it is the cause behind nearly every routing failure in
this flow:

> Geometry inside an instance cannot be resolved to a net.
> `_collectPhysicalRects` can attribute only PORTS, through the node
> graph, so a device's own internal rails arrive as `"?"`.

That forces a bad choice, and the router currently takes the permissive
side: unattributed metal is *tolerated* on the pin layer, because
treating it as foreign blocks a via off every pin by the pin's own
metal. The cost is exactly what the five failures are — a run or a via
pad landing on a device rail, which the connectivity flood then
relabels, merging two nets that never touched a wire.

It has now been hit three separate ways:

1. a run along the pin layer tying a device's D to its own S through a
   side strip (fixed narrowly: `TrackMap.column_metal` +
   `_pin_layer_if_clear`, cicpy bc5265e)
2. a via pad on the same strip (**not fixed** — this is the 5 above)
3. the connectivity flood mislabelling the strip, so the short report
   names two signal nets and points at the router, when the geometry
   belongs to neither

### The fix worth making

**Attribute instance geometry.** An `Instance` knows its cell and its
port-to-net mapping, so a rect inside it that coincides with a port rect
belongs to that net. Everything else inside the instance belongs to *no*
net and is a hard obstacle — not "unknown, tolerate", which is what it
is treated as now.

That single change:

- makes device rails real obstacles, so vias and runs stop landing on
  them — the 5 shorts above
- lets the flood stop inventing net labels for them, so short reports
  name the real culprit
- retires `TOLERATE_UNATTRIBUTED_ON`, `column_metal` and the pin-span
  widening in `_pin_layer_if_clear`, all of which are workarounds for
  not having it

`trackmap.py` already names this as the proper fix and calls it "the
same job as step 2b was for pins". It is the highest-value change left
in the router.

## Then: the top instantiates the stacks

Two things remain after LVS passes.

**Fill devices.** The layout has them, the schematic does not: measured
on one stack, 7 devices in the extracted netlist against 6 in the
schematic. The same gap exists at the top (2 `xfill` in the extracted
`.spi`, 0 in the CDL) and is invisible there only because the top has
never passed LVS anyway. A stack cell has nowhere to hide it. Either
`stack_subckt` emits the fill devices, or the stack `.mag` excludes
them. Emitting them is the honest one — they are real transistors.

**A hierarchical top.** Today `write_stack_cells` publishes stack cells
*alongside* a parent that still contains the devices — deliberately, so
a working flat design is not disturbed. The last step replaces that: a
top schematic that instantiates the eight stack symbols instead of ~70
devices, with `plan_stack_cells`'s `ports` as the connections. All the
information needed is already computed.

The payoff is the point of the exercise: the top stops being 70 devices
and ~2000 rects and becomes 8 instances routed port to port, and each
stack is verified before the top exists.

## Order of work

1. attribute instance geometry (the fix above) — unblocks everything
2. re-measure the 8 stacks with `boundary=True`; expect all clean
3. fill devices into `stack_subckt`
4. per-stack LVS as a gate in the flow
5. emit the hierarchical top

Do not skip to 5. Each level must be LVS clean before the next is built
on it — that is what makes the decomposition worth having rather than
just tidier.

## State the design was left in

`LELOTEMP_OTAR`: **0 DRC, 0 shorts, 11 opens**, `STACK_ROUTING =
("r_deg", "p_sw")`, `STACK_BOUNDARY = False`. All 8 stack cells
generate and pass DRC standalone. The 11 opens are group- and top-level
signal routing that the hierarchy is meant to replace, so they are not
worth chasing flat.
