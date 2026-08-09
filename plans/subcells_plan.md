# Subcells: generate once, instantiate in the top

Goal: stop laying out a big analog cell as one flat field of devices.
Generate each subcell as a real cell -- its own `.mag`, `.sch`, `.sym`,
its own DRC and LVS -- and have the top instantiate those cells and
route only between their ports.

**A subcell is not a stack.** Three ways to be one, in priority order:

1. an entry in **`<CELL>.subcells.yaml`**, the sidecar beside the
   pycell -- name, member regex, and the KIND of unit:

       subcells:
         - name: p_in
           match: "^(xbl[45]|xbl[12]<\\d+>|xstack_p_in_[ab]_(top|bot)|xfill_p_in_[ab]_\\d+)$"
           type: diffpair          # stack | diffpair | mirror

   Declarative on purpose: a subcell is a statement about the design,
   and a statement belongs in data, not in whichever pycell hook builds
   the groups. First entry wins, so order specific to general.
   Measured on the OTA: this exact entry merges the two input columns
   into one `LELOTEMP_OTAR_P_IN` with the diffpair's whole port list --
   `VD1 VD2 VD3 VDD_1V8 VIN VIP VS` -- which is the pair-symmetry unit
   the flat flow could never mirror.
2. any CellGroup with `subcell = True` set on it.
3. failing both, every stack -- a column of devices being the
   decomposition that needs no thought.

`subcell_membership` and `subcell_groups` follow the same rule and have
to stay in step.

**The type picks the router, and only the stack router exists.** A
declared `diffpair` or `mirror` wants symmetry or gate bussing that a
series-link search knows nothing about, so `route_stack_level` declines
it with a warning instead of routing wrongly -- a pycell routes any
type and takes precedence anyway. Writing the diffpair router (route
the halves identically, mirrored) and the mirror router (bus the gates)
is where the type becomes worth more than documentation. The OTA does
not ship the p_in declaration until one of those exists: it would trade
two clean stack subcells for one that nothing can route.

Everything below is measured on 2026-08-08, on a 70-device OTA
(`LELOTEMP_OTAR`, 8 stacks). Numbers are from the tools, not estimates.

## Where it already works

The generation machinery is done and verified:

| step | state |
|---|---|
| `plan_subcells` — names, instances, ports, internal nets | works |
| `run_stack_pycells` — a stack's own `<CELL>.py route(layout, entry)` | works, runs between afterPlace and beforeRoute |
| `route_stack_level` — search-based routing per stack | works |
| `write_stack_cells` — publishes each one as a cell, writes `.mag` | works |
| `stack_subckt` — the generated subckt | works |
| `cicpy sch2subcells` / `make subcells` — `.mag`, `.cic`, `.sch`, `.sym` per subcell, parent untouched | **works** |
| **standalone DRC of every generated subcell** | **all 8 clean** |

The flow is two steps now, and the order is the point:

    make subcells CELL=X     a cell per subcell, parent never written
    make mag      CELL=X     the parent

That replaced a second `transpile --xschem` carrying a negative
lookahead over the cell name, which had to be documented as "not
optional" because getting it wrong wrote a generated schematic over the
hand-drawn source. The list comes from the plan by name now.

Four bugs had to go first, all of which made a generated cell lie:

- the printer never looked for symbols in the library it was writing,
  so transpiling a generated cell died on its own devices
- a symbol read and written back grew a duplicate `K` block per run
- a cell being printed found its OWN previously generated `.sym` and
  replayed it, freezing its port list — and xschem takes the subckt
  ports from the symbol, so a new port appeared in `*.PININFO` and was
  missing from `.subckt`
- **a net that is a port of the parent is a port of the subcell**, even
  when every device pin on it sits inside one subcell. An input pair's
  gate had all six pins in one column, so the cell swallowed it and
  there was no way to drive it once the parent instantiated the cell

Before those, the generated schematic put every wire on a placeholder
pin grid touching nothing, xschem connected nothing, and netgen merged
six identical devices into one — which reads as "6 devices, 24 wires"
and looks like success.

So a subcell can be generated and is DRC clean. What it cannot yet do
is pass **LVS**, and that is the whole gate.

## The one thing in the way

**A subcell must join every net it has two or more pins of** —
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

## A subcell `.cic`, for the route checker

`sch2subcells` writes a `.cic` per subcell so the MCP route tools work
on one subcell instead of the whole cell. Verified: `blockers` on a
subcell reports the same 110 pin spans as the parent does over the same
box, and `cell_info` reads the placement and ports.

Two things that had to be right:

- **the cut cells travel with it.** A route that changes layer places an
  `InstanceCut` referring to `cut_<A><B>_NxM`, and a `.cic` that does
  not define those cells resolves the via to nothing -- so the checker
  reads the corridor as empty and answers "nothing blocks". A wrong
  "nothing blocks" is worse than an error.
- **the device library still has to be passed in**, with `--I`. The
  subcell holds instances, not device geometry, and without the include
  every pin is invisible.

`tracks` on a subcell whose routing is all on the pin layer says "no
geometry on any routing layer". That is correct, not a failure: the pin
layer has no `ROUTE.directions` entry and therefore no tracks.

**Open, and it belongs with the boundary work:** a subcell generated
with `boundary=True` came out with its M2 wires and **no `InstanceCut`
at all** -- wires floating over the pins they should land on. Whether
route.py is not placing the vias or `write_stack_cells`'s copy is
dropping them was not established; the parent on disk was a
`boundary=False` build, so it could not be used to tell the two apart.
Settle that before trusting any boundary-routed subcell.

## Then: the top instantiates the subcells

Two things remain after LVS passes.

**Fill devices.** The layout has them, the schematic does not: measured
on one subcell, 7 devices in the extracted netlist against 6 in the
schematic. The same gap exists at the top (2 `xfill` in the extracted
`.spi`, 0 in the CDL) and is invisible there only because the top has
never passed LVS anyway. A subcell has nowhere to hide it. Either
`stack_subckt` emits the fill devices, or the subcell `.mag` excludes
them. Emitting them is the honest one — they are real transistors.

**A hierarchical top.** Today `write_stack_cells` publishes subcells
*alongside* a parent that still contains the devices — deliberately, so
a working flat design is not disturbed. The last step replaces that: a
top schematic that instantiates the eight subcell symbols instead of ~70
devices, with `plan_subcells`'s `ports` as the connections. All the
information needed is already computed.

The payoff is the point of the exercise: the top stops being 70 devices
and ~2000 rects and becomes 8 instances routed port to port, and each
subcell is verified before the top exists.

## Order of work

1. attribute instance geometry (the fix above) — unblocks everything
2. re-measure the 8 subcells with `boundary=True`; expect all clean
3. fill devices into `stack_subckt`
4. per-subcell LVS as a gate in `make subcells`
5. emit the hierarchical top

Do not skip to 5. Each level must be LVS clean before the next is built
on it — that is what makes the decomposition worth having rather than
just tidier.

## State the design was left in

`LELOTEMP_OTAR`: **0 DRC, 0 shorts, 11 opens**, `STACK_ROUTING =
("r_deg", "p_sw")`, `STACK_BOUNDARY = False`. All 8 subcells
generate and pass DRC standalone. The 11 opens are group- and top-level
signal routing that the hierarchy is meant to replace, so they are not
worth chasing flat.
