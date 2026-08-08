# A scoped maze router

The present router places geometry by heuristic and then finds out what
it hit. This is the plan for replacing it with a search that knows what
is in the way, and for giving that search a scope small enough to be
solvable.

## What was measured, 2026-08-08

`LELOTEMP_OTAR` was routed by hand through the existing API. Three nets
cross between the device rows — `VDS`, `VS`, `VO` — and every attempt to
place them failed in one of two ways. Both are worth stating precisely,
because they are what the new router has to be right about.

### 1. Bars land where the pins are, not where there is room

A plain `addConnectivityRoute` takes its bar height from the net's own
pins. Measured with the `tracks` tool:

- `VDS`'s horizontal bar sat at **y 365000 — inside the pmos row**.
- The `mid` channel between the rows held **27 free M3 tracks** over the
  span `VO` needed, and nothing had ever been sent there.

Five full regenerations were spent asking *which layer* instead. The
answers, all measured, are a catalogue of the wrong question:

| layer | result |
|---|---|
| M2 | closes, 5 DRC — met1.2 / met1.7 at the via's M1 pads |
| M3 | shorts to `VDS` |
| M4 | closes, shorts to the `VS` strap in `p_in_a` |
| M5 | closes, 8 DRC — via3.1, the M1..M5 stack is too tall |

`addOrthogonalConnectivityRoute` with `hchannel`/`htrack` fixes this
half completely. Given a track each the three bars separate cleanly —
`VDS` 269000/273000, `VS` 285000/289000, `VO` 301000/305000 — and all
three nets close. **The layers were never full. The bars were in the
wrong place.**

### 2. Trunks run through other nets' pins

The vertical half still collides, and `vtrack` cannot fix it because it
is not a lane problem. Every pair fails identically: **two nets whose
pins sit at the same x in one column, so the lower net's trunk runs
through the upper net's pin.**

- `VDS`/`VS` both drop into the resistor at x 265200..274200, because
  `REYATR_RES_36C2F0` puts P and N on the same left contact band. `VS`
  reaches y 57300 and passes `VDS`'s pin at 105300.
- `VDS`/`VO` both drop into the bias column; `xba1` and `xba8` are both
  at x 16.480.

This is the same shape as the five ladder nets, and as the `R1<0>`/
`R1<1>` link that the vertical `RPPO4` could not route. It has been
rediscovered at least four times. **A router that treats pins as
obstacles cannot hit it at all**, which is the single strongest argument
for the search.

## The design

### Route by LEVEL, not by net

The first version of this plan classified NETS by scope: VO spans three
groups, so VO is a top-level net, routed whole. That framing is what
made VO hard, and it was wrong.

Every net is routed at every level it touches, innermost first:

    1. stack   every net, inside every stack it has 2+ pins in
    2. group   between the stacks of a group, against their boundaries
    3. top     between groups

A large net is never posed as a large problem. Measured on
LELOTEMP_OTAR, 13 open nets of up to 33 pins decompose into **19
stack-level subproblems and 13 inter-stack hops**:

    VO        3 pins -> xba:2, xnd:1                    + 1 hop
    VDD_1V8  33 pins -> xba:12, xbl:14, xbs:7           + 2 hops
    VD1      14 pins -> xbl:6, xnd:7, xns:1             + 2 hops

VO stops being the hard net. It is one two-pin route inside xba and one
hop, and the hop is between boundary ports rather than through
everything in between.

**Each level must be LVS clean before the next is built on it.** That is
what makes the decomposition worth having rather than just tidier: a
short at stack level is found against a handful of instances, not
against 1969 rects at the top.

### Scope is a cell, and stacks become cells

Promoting each stack to a cell is what makes the levels real rather than
a convention:

- its own `.mag`, its own extracted netlist, and therefore **its own
  LVS**, which is what level 1 has to pass before level 2 exists.
- ports on its boundary. At the parent level a stack's internal pins are
  not visible, so no route can pass through one -- and a level-2 route
  aims at a port whose position was decided once, by the child.
- reuse: two identical stacks are one cell.

### The search

A* on a 3D grid of `(track_x, track_y, layer)`:

- **nodes** — track intersections, from `TrackMap`, which already builds
  per-layer occupancy with net attribution and already accepts an
  `extent`. `build()` calls `layout._collectPhysicalRects()` with no
  argument; `_collectPhysicalRects(obj=...)` already takes a subtree, so
  **scoping TrackMap is a one-argument change, not a rewrite.**
- **edges** — a step along a layer's preferred direction, and a via to
  an adjacent layer.
- **costs** — length; a via cost that reflects the real pad, because
  a pad is 8800 across and adjacent 4000-pitch tracks clash on pads
  before they clash on bars; a penalty for crossing a channel off its
  preferred direction.
- **obstacles** — occupied track spans, and *other nets' pins*, which
  the present router does not model at all.
- **admissible heuristic** — Manhattan distance in track counts plus
  the minimum via count for the layer delta. Dijkstra is A* with h=0;
  start there, since correctness is the goal and the grids are small.

### Independent of the old router

New module, `core/mazerouter.py`, and a new entry point. It does not
touch `route.py`. The existing `addConnectivityRoute` and
`addOrthogonalConnectivityRoute` keep working, and a design opts in per
net. Power stays on the existing `addRouteRing`/`addPowerStrap` — rings
and straps are not a search problem and the user has excluded them.

## The obstacle is a via COLUMN, not a track overlap

The most important correction this plan has had, and it only appeared by
testing the mechanism against the failure it was built for.

`crosses_pin` on a layer finds nothing. VS's trunk is on M4 and VDS's
pin is on M1; they never share a track, so a same-layer test rejected
**0 of 3** candidate tracks for the one collision known to exist. The
model was right that pins are obstacles and wrong about what they
obstruct.

What collides is the via column. A route reaching a pin must come down
through every layer at that x, and any other net's pin in that column is
shorted. Asked that way, on the same layout:

    column_blockers("VS", x 265200..274200, y 57300..290700)
      -> VDS  at y 104000
         R1<0> at y 64000

VDS at y 104000 is exactly the pin the short report blamed. A control
band with nothing in it returns clean, and a net does not block itself.

This is now `TrackMap.column_blockers`, with seven regression tests in
`tests/unittests/test_trackmap_pins.py` including one that asserts the
same-layer test does NOT catch it -- so if anyone simplifies the column
check back to a per-layer one, the reason is in the failure message.
The tests were verified to fail when the mechanism is sabotaged.

**For the router this sets the cost model.** A via column is not a point
cost; it is an exclusive claim on (x, y-range) across all layers, and it
is 8800 wide because that is the pad. Two nets wanting the same column
is the conflict to search around, and it is why "which layer" was always
the wrong question.

## Pin attribution: closed

Attributing a pin from its own port name gives `B`, `S`, `P`, `N` --
the subcell's names for its own terminals, which say nothing about the
net the instance is wired to. Pins are now read from
`nodeGraph[net].ports` instead, the same source `_directNodeAccessRects`
routes from, so the map and the router agree by construction. 1700 pin
spans over 20 real nets on OTAR.

## Step 3, built: what the search found that the plan did not predict

`core/mazerouter.py`. Dijkstra over (track_x, track_y, layer), moves
along a layer's direction or a via between adjacent layers, obstacles
from the pin-aware TrackMap. Nine tests in
`tests/unittests/test_mazerouter.py`, verified to fail when the pin
check is sabotaged.

It works: a clear horizontal span comes back as a straight run on one
layer, and a layer change on top of a foreign pin is refused and routed
around -- out along M3 clear of the pin's x-span, up, and back.

Three things only appeared by running it, and all three are worth more
than the code:

**The grid was unbounded.** `TrackMap.track_at` returns the NEAREST
track, so it answers for coordinates far outside the cell. The first
search wandered off and did not terminate in five minutes. `in_bounds`
against the scope extent fixes it, and it is a reminder that the scope
is not just an optimisation -- without a boundary the search has no
reason to stop.

**Obstacle queries must be indexed, not scanned.** `column_blockers`
walks every track on every layer, which is right for a question asked
once and ruinous per node expansion. Bucketed once per search: 3741
boxes, 1000 via checks in 0.010s. Deduplicating mattered too -- one pin
spans many tracks and was indexed 45 times.

**A via pad is wider than the resistor's pin pitch, and that is the
whole story.** The resistor's terminals are 4000 apart; a via pad is
8800. A pad centred on one covers the other, so NO layer change is
possible directly on either pin -- not by another net, and not by the
net that owns it. This is the physical fact under every hand-routing
short, and no amount of track or layer picking could have fixed it. The
router is right to detour, and it is the first thing in this codebase
that can even state the constraint.

## Step 3b, built: paths become geometry

`MazeRouter.segments` collapses a path into runs and vias;
`MazeRouter.emit` draws them. Kept apart from the search on purpose --
searching has no side effects, so a path can be inspected, asserted on
and diffed before a layout ever changes. Four more tests.

Measured on the detour around VDS's pin: 34 path nodes become 4 runs
and 3 vias --

    M3 270000,104000 -> 234000,104000     west, clear of the pin span
    M2 234000,104000 -> 234000,116000     up, where a via is legal
    M3 234000,116000 -> 270000,116000     back east
    M4 270000,116000 -> 270000,104000     down to the target

-- and every via lands at a column `via_is_free` accepts. A straight run
in the free channel collapses 14 nodes to a single rect with no vias.

## Step 3c: VO is routed, by search

The net route.py could not place at all. 13 opens -> **12, 0 shorts,
0 DRC**, and the path is one the old flow would never have found:

    M1 at xnd4's pin in the nmos row
    M2 up   126000, 220000 -> 340000
    M3 east 126000 -> 207000  at y 340000   <- the MID CHANNEL
    M2 up   207000, 340000 -> 408000        -> xba2's pin

y 340000 is inside the mid channel, which held 27 free M3 tracks the
whole time and had never been used, because a plain route takes its bar
height from the net's own pins. The search is not choosing a layer, it
is choosing a path, so the channel is simply where the cheapest path
goes.

One bug on the way, and a nasty one: **`Cut.getInstance` already returns
a fresh `InstanceCut`** and registers the cut cell for
`Design.addCuts()` to hoist. Taking a `getCopy()` of it produced
something the printer did not recognise as an instance -- the wires
appeared in the .mag and **not one via did**, so the net stayed open
with nothing in any report to say why. Only measuring the .mag for via
geometry found it. Regression test added, verified to fail when the
getCopy() is put back.

Note also that a unit slip cost a cycle here: mag coordinates are
internal/50, not internal/5, so a first check "found" no geometry that
was in fact present.

## The obstacle model was wrong three ways, and VO's success was luck

Routing the stack-local nets exposed three errors in the model, all of
which had been asserted confidently -- one of them in this plan, in a
commit message, and in the field guide.

**1. The via pad was a guess.** VIA_PAD was 8800, carried over from a
note about pad clashes. The real sky130 1x1 cut is **4000 square**,
which `Cut.getInstance(a, b, 1, 1).width()` will say. At 8800 the router
could not leave a pin anywhere in the switch column, where pins sit 4000
apart, and reported all five ladder nets unroutable. It also produced
the claim -- written up as a "physical fact" -- that no layer change is
possible on either resistor terminal. **That claim is retracted.** A via
centred on one terminal reaches 2000; the neighbour at 4000 is clear.

**2. A via was treated as claiming every layer.** True of a whole
descent from M4 to a pin, false of one M1->M2 step. It made an M1->M2
via illegal beneath VS's unrelated M4 trunk, which is not a short in any
technology, and blocked every ladder net at its own pin.

**3. Wire extents were merged.** `Track.spans` collapses a net to one
min/max, so a net appearing twice on a track appeared to occupy
everything between. Wires now keep exact intervals.

And **unattributed metal cannot be treated as foreign**.
`_collectPhysicalRects` can only attribute PORTS; a device's internal
rails all arrive as "?". Blocking on them blocks a via off every pin by
the pin's own metal. So "?" does not block -- at the cost, stated
plainly, that a via can land on a device's internal rail unnoticed. It
is bounded, because the electrically interesting M1 in a device is its
ports, and those are attributed.

**The consequence for OTAR is a retreat.** With the corrections the
search finds a *shorter* path for VO, and that path overlaps the VS
strap in p_in_a. The committed VO route was found by the over-strict
model, so it was conservative enough to miss VS by accident. The route
is stood down and the net is open again: 13 opens, 0 shorts, 0 DRC.

That is worth being blunt about. VO closing was reported as the router
beating the old flow, and the honest version is that it closed because
the model was too cautious to find the path that shorts. The router is
now more correct and the layout is back where it was.

## What the ladder attempt showed

With the model fixed, all five ladder nets find paths -- the shape that
had defeated four hand attempts. Drawing them exposed the next real
limitation rather than a modelling one: routed one after another,
net1..net3 succeed and then net4 and net5 are blocked by the geometry
net1..net3 just drew. Greedy net-at-a-time ordering with no rip-up.

So the order of work gains a step that was not in the plan: **the router
needs to route a SET, not a net.** Ordering by constrainedness, or
rip-up-and-retry when a later net fails, or negotiated congestion. Until
then it can close some nets in a column and will strand the rest.

## Level 1 measured, 2026-08-08

Feasibility, each subproblem scoped to its own stack extent: **27 of 28
routable**, including all five ladder nets. Whole-cell routing could
place only 3 of those 5 -- scoped, the search has the room that
whole-cell routing had already spent. Only VBP in xba fails.

Drawn for real (sequential, map rebuilt per net): **24 of 28 routed,
LELOTEMP_OTAR 13 opens -> 9**, and **1 short**, VD2 into VS.

So level 1 is NOT clean, and by its own rule nothing may be built on it
yet. The short is not blindness: VS and VDS are both present in the
track map as attributed wire, so the router saw them and drew into one
anyway. The suspect is the width of the emitted rect against the track
the step was checked on -- `is_free` tests the track's span along the
route, while `emit` draws a rect half a pitch either side of the
centreline, so a run can be legal on its own track and still overlap a
neighbour's wire. Next cycle starts there.

Also worth stating: this cell already carries hand-drawn top-level
routes for VS and VDS, which cut across every stack. They predate the
hierarchy and they are what level 1 keeps colliding with. The real test
of the model is to remove them and let the router do all three levels.

## Order of work

1. **Scope `TrackMap`** to a subtree — pass `obj` through to
   `_collectPhysicalRects`. Smallest change, immediately useful to the
   `tracks` tool.
2. **Pins as obstacles.** DONE. `_collectPhysicalRects(include_ports=)`,
   `Track.block/blocking/crosses_pin`, `TrackMap(block_pins=)` and
   `free_for(net, ...)`. M1 joins the map when pins are modelled,
   because that is where all 213 of OTAR's pins are.
2b. **Resolve pin nets through the node graph.** DONE.
2c. **`column_blockers`.** DONE -- and it, not `crosses_pin`, is what
   the router must ask.
3. **Dijkstra over one scope.** DONE -- `core/mazerouter.py`, 9 tests.
   Still returns a PATH, not geometry; nothing is drawn yet.
3b. **Emit geometry from a path.** DONE -- segments() and emit().
3c. **Route one real OTAR net end to end.** Done, then stood down --
   see above. The mechanism works; the route it now finds shorts.
3d. **Route a SET of nets, not one net.** Ordering, or rip-up and retry.
   Without it, net-at-a-time strands whatever comes last: measured,
   net1..net3 route and then net4, net5 cannot.
3e. **Make the wire check catch what VO's shorter path hits**, then
   re-enable VO.
4. **Promote a stack to a cell** and LVS it standalone. `r_deg` is the
   right first subject — it is 4 instances and already has clean LVS as
   `HRPPO12`, so a mismatch is the promotion's fault and nothing else.
5. **Hierarchy** — the three scopes, in order.
6. A\* heuristic, only once Dijkstra is correct.

## What would prove it

`LELOTEMP_OTAR` at **0 opens, 0 shorts, 0 DRC**. It is at 13 / 0 / 0
today. `VO`, the five ladder nets and `R1` are all the same shape, so a
router that closes one should close all of them — and if it closes only
some, the difference is the measurement worth having.

## Escape direction is a degree of freedom, not a cell defect

An earlier draft of this plan concluded that P and N sharing a contact
band was a cell defect needing an M1 jog or an odd stripe count. That is
wrong. Two pins at the same x do not have to be left by the same route:
`-|--` (LEFT) and `--|-` (RIGHT) escape on opposite sides, and
`offsetlow`/`offsethigh` shift the escape within a side. Nothing has to
run through anything.

Measured on LELOTEMP_OTAR, 2026-08-08:

- All three crossings escaping LEFT (`-|--`): **0 shorts.** The escape
  does remove every collision. But all three then read open -- an escape
  leaves the pin without completing the far end.
- Channel routes (`hchannel`/`htrack`) **close all three** but short,
  because the pin drops still land together.
- Channel routes plus `offsetlow`/`offsethigh`: still close all three,
  still short. The offset is one routing width and a via pad is 8800
  across, so the pads clash before the wires do.

So the two halves are each solved and do not compose by hand: the
channel completes the route, the escape separates the pins, and nothing
in the present API applies both with an offset large enough to clear a
pad. **That composition is precisely what the search is for.** The
router must treat, per net:

    escape side      left or right out of the pin
    escape offset    quantised to the VIA PAD, not the wire width
    channel + track  where the long haul runs
    layer            where a via is cheaper than a detour

as one cost-minimised choice rather than four independent options a
human sets in sequence. Every failure above is a pair of those four
chosen well and the other two chosen blind.

## What this does not fix

Nothing here helps a net whose two pins are genuinely enclosed — a port
reachable only through another net's geometry, with no escape on either
side. No such case has been found in OTAR: every one that looked like it
turned out to be an escape the API could express and a human did not.
Worth stating, so that if the router fails on one, that failure is known
to be a new shape rather than this one again.
