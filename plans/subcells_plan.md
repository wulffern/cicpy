# Subcells: generate once, instantiate in the top

Goal: stop laying out a big analog cell as one flat field of devices.
Generate each subcell as a real cell -- its own `.mag`, `.sch`, `.sym`,
its own DRC and LVS -- and have the top instantiate those cells and
route only between their ports.

**A subcell is not a stack.** Three ways to be one, in priority order:

1. an entry in **`<CELL>.yaml`**, the cell's sidecar beside the
   pycell -- `subcells:` is its first key, not its last; name, member
   regex, and the KIND of unit:

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

## State, 2026-08-09: the first subcell passes LVS

    LELOTEMP_OTAR_P_IN_A, boundary routed, standalone:
    Final result: Circuits match uniquely.

Instance geometry is ATTRIBUTED now (`_attributeInstanceBody`): the
rect under a pin takes the pin's net, the net floods through same-layer
touching metal, and what is left is `device_metal` -- blocked for every
net, never tolerated. The flood is load-bearing: direct overlap alone
left the pin's own conductor one row up as an obstacle, and every
boundary net came back "no path, closest approach 0 away". Fill devices
are emitted in the generated schematic the way magic extracts them --
terminals floating, bulk on the supply, bulk position read off the
siblings. Copied vias are real InstanceCuts, not flattened Rects.

Measured, all 8 with `boundary=True`:

| subcell | boundary nets | result |
|---|---|---|
| `p_in_a` | 4/4 routed | **LVS: Circuits match uniquely** (20 met1.2) |
| `p_in_b` | 3/4 | clean, 1 blocked |
| `r_deg`, `p_sw` | partial | clean, 1 blocked each |
| `p_bias`, `n_load_a/b`, `n_mirr` | most routed | **1 short each** |

## State after the routing round of 2026-08-09

`make hier` exists: the top as eight subcell instances, identity
transforms, DRC clean, extracted hierarchically by magic.

The boundary sweep stands at **6 of 8 shorts-free** (was 4), p_in_a
DRC clean + LVS matched standalone. What that round fixed, each
measured before and after:

- **M1 is the cheapest layer** (`ROUTE.pintravel` + `ROUTE.costs` in
  the tech; the search may travel the pin layer, priced lowest).
  Attribution is what made it safe.
- **claims are consulted by every shape** -- the facing vertical and
  the terminal lane used to bypass `taken()`, and the bend branch fell
  back onto a claimed column when nothing was free. A net with no
  clear column is BLOCKED now, which is truthful.
- **landings are claimed, not only trunks** -- a routed net's pins,
  and the PARENT's queued routes overlapping the stack extent (the
  top's power-up route lands on a gate inside the load column).
- **a cut never bigger than the pin it lands on**
  (`Cut.getCutsForRects`): the 1x2-on-a-4000-tab shorts are gone.

## What remains: pad POSITION

Both remaining shorts (n_load_a, n_load_b) are one mechanism: a pad
LEGAL ON ITS OWN PIN whose 8800 width overhangs into the diagonal
gate tab beside it. The cut fits the pin; the pin's free width from
the trunk to the neighbour is smaller than the pad. The fix is to
shift the pad along the pin away from foreign geometry -- route.py's
cut placement needs the keep-out, which it still does not have.

The blocked-not-shorted nets (one or two per subcell, mostly supplies
and diode nets with no clear column) come after; blocked is correct
until the landing is legal.

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

## The placement hierarchy (the current frontier)

The flat afterPlace builds the hierarchy from devices every run. The
target is the inverse: `spi2mag` on `<CELL>_HIER.spice` (generated,
tracked), placing EIGHT SUBCELL INSTANCES the way it places any
library cell, with a pycell that is two rows and an abut. What stands
in the way, measured:

- **subcells are not origin-normalised**, and cannot be by simple
  translation: they hold the parent's own instance objects, so
  translating one drags the parent's devices (2 shorts, 23 DRC).
  The restructuring step -- instances leaving the parent, cell copies
  or real ownership transfer -- is where normalisation happens.
- **the subcell .mag must place from maglib** like any primitive:
  ports exist, `placed_at` records the cut offset.

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
