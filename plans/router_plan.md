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

### Scope is a cell, and stacks become cells

The rect-getting functions are the problem the user identified:
`getNodeAccessRects` and `TrackMap.build` see the whole design, so every
route is planned against every other route in the cell. Restricting the
*query* is not enough — the fix is to make the scope a real hierarchy
boundary.

**Promote each stack to a cell.** A `CellGroup` that today is a
placement convenience becomes a subcircuit with:

- its own `.mag`, its own extracted netlist, and therefore **its own
  LVS**. Errors are caught at the stack, not at the top, where a single
  short currently hides behind 1969 rects.
- ports on its boundary. This is the part that kills failure mode 2:
  at the parent level a stack's internal pins are not visible, so no
  trunk can pass through one. The parent routes to a *port*, and where
  that port sits is the child's decision, made once.
- reuse — two identical stacks are one cell.

### Three scopes, outermost last

    intra-stack   inside one stack cell. Obstacles: that cell only.
                  Produces the boundary ports.
    intra-group   between stacks of a group. Obstacles: the group's
                  stack cells as solid blocks + their ports.
    inter-group   the top. Obstacles: group cells as solid blocks.

Each level sees O(10) obstacles rather than O(1000) rects, which is what
makes A* cheap enough to run per net and admit a real cost model.

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

## Order of work

1. **Scope `TrackMap`** to a subtree — pass `obj` through to
   `_collectPhysicalRects`. Smallest change, immediately useful to the
   `tracks` tool.
2. **Pins as obstacles.** Teach `TrackMap` to mark other nets' pin rects
   as blocked, not merely occupied. Failure mode 2 becomes visible in
   the `tracks` report before anything is drawn.
3. **Dijkstra over one scope**, no hierarchy yet. Validate on
   `LELOTEMP_OTAR`'s `mid` channel against the known answer: the bars
   must land on the free tracks the `tracks` tool already reports.
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

## What this does not fix

The resistor cell still puts P and N on the same contact band. A router
that models pins as obstacles will route *around* that, at the cost of a
detour per net; putting the terminals at opposite ends of the cell
removes the detour. That is a cell decision — it needs either an M1 jog
across the cell or an odd stripe count, and an odd count costs the
gradient cancellation the series pair exists for — and it is worth
taking separately from the router.
