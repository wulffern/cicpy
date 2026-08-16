---
layout: page
title: Agent layout guide
---

* TOC
{:toc}

# Layout with cicpy, a field guide

This page is the operational guide for doing schematic driven layout with
cicpy. It is written for agents, but everything in it applies to humans.
The API reference lives in [pycell](pycell.md), [layout](layout.md) and
[routes](routes.md), this page is about *how to work*: the loop, the
conventions, and the facts about the libraries and the design rules that
are expensive to rediscover.

**This page drifts behind the code, and has.** It described the sidecar
and the flat router for weeks after `layout.path()` stories,
`addBlockChannel`, `Bus` and `CICPY_TRACE` landed — the whole vocabulary
a top level actually routes in. When something here disagrees with
`src/cicpy/core/`, the source is right; and if you find a gap, fix this
page in the same commit. Check `git log -- docs/agent_layout.md` against
`git log src/cicpy/core/` before trusting a section you are about to
lean on.

## Start here: a cell is a SidecarCell unless you know why not

**Write every new cell as a `SidecarCell`.** Not "for a large analog
cell" — for all of them. The classic pycell (module-level hooks and
`data`) still works and is still the escape hatch, but it is no longer
the thing to reach for first, and choosing it is a decision that needs
a reason.

The reason is not style, it is what the router can see. A flat cell is
routed by the connectivity router, which draws a shape from a net's
own pins and a lane you name; it cannot see what is already there, so
two nets are kept apart only by the lanes you assign them. That works
until the cell has more nets than obvious lanes, and then every fix
moves the collision instead of removing it. Measured on LELOTEMP_CMPR
— four columns, seven crossing nets, M2/M3/M4 free — about twenty
builds took it from six merged nets to one and never to zero, and not
one of the shorts was two wires crossing on a layer. They were via
COLUMNS and rails sitting on foreign pins, which no track map shows
and no lane assignment prevents.

A SidecarCell splits the same netlist into one cell per column and
hands each to the stack-level maze router, which *is* space-aware and
gives its conclusions back as **anchored stories** ready to paste into
the design. What you declare at the top is only the nets that cross
between columns, each a story through named corridors. A story in a
channel cannot land on a pin, because a channel is the place where
there are none.

Two things to carry into it, both measured:

- **The drops are where a channel design still shorts.** The bars sit
  on their own tracks and stay apart; the vertical drops from a bar
  into a column do not, because every net whose pins are on one
  terminal of that column publishes its port at the same x. Two nets
  on the same terminal drop in the same lane, and a via pad is 0.88 um
  against a 0.6 um lane, so even neighbouring lanes overhang. Give
  the drops `align` and `cuts`, or publish the subcell's ports at
  distinct x.
- **Supplies are not part of this.** See "Supplies go to the guard".

## The sidecar flow — how it works

Everything below this section still works and is still the reference
for the primitives, but since 2026-08 the way to lay out a large
analog cell is **hierarchical and declarative**: one python sidecar
beside the design holds the whole truth — one class per cell, one
nested class per subcell, all in `<CELL>.py`. `LELOTEMP_OTAR` in
lelo_temp_sky130a is the worked example — eight subcells and the
top, all DRC clean and LVS "Circuits match uniquely", from one
`LELOTEMP_OTAR.py`.

The classes are REAL: `Stack` subclasses the core `StackGroup`, and
the recipe builds the declared class itself, so a hook's `self` is
the group that was actually placed — `self.addConnectivityRoute` is
group-scoped, `self.layout` is the parent, and a rename in
cellgroup.py breaks the design file loudly instead of silently.
`SidecarCell` subclasses both the recipes AND `LayoutCell`, so the
class IS the cell being built and is handed to itself as the pycell
— every hook it declares runs, in both passes. A cell that needs
more than declarations overrides
`beforePlace/afterPlace/beforeRoute/afterPaint/place/route` and
calls `super()`; ask `self.assembled` when the override is only
right in one of the two passes.

### One class, one cell

`design/<LIB>/<CELL>.py`:

```python
from cicpy.sidecar import SidecarCell, Stack, Mirror

class LELOTEMP_OTAR(SidecarCell):

    place = {"groupbreak": 6, "channel": 6}  # flat-build knobs

    class p_bias(Stack):                # class name = subcell name;
        match = r'^(xba\d+|xstack_p_bias_(top|bot)|xfill_p_bias_\d+)$'
        group = "pmos"                  # base = Stack|DiffPair|Mirror
        channel = "bias"                # named vertical channel
        order = ['xba1', 'xba8', 'xba2', 'xba6', 'xba7', 'xba3']

        def beforeRoute(self, entry):   # self IS the built group
            self.layout.addConnectivityRoute(...)  # parent-scoped
            self.addConnectivityRoute(...)         # group-scoped
            return None                 # True = fully routed here

    class r_deg(Stack):
        match = r'^(xd2<\d+>|...)$'
        fill = False                    # no dummy fill for resistors

    rows = [                            # the floorplan, bottom row
        [n_load_a, n_load_b, n_mirr, r_deg],   # first; the classes
        [p_in_a, p_in_b, p_bias, p_sw],        # themselves, so a
    ]                                          # typo is a NameError

    supplies = [                        # rings + strap connections
        {"net": "VDD_1V8", "ring": "t", "strap": "top",
         "guard_exclude": "^xbs6$"},
        {"net": "VSS", "ring": "b", "strap": "bottom",
         "strap_exclude": "^xd2<[1-9]"},
    ]

    #- the assembled top IS the cell, so its declarations sit on the
    #- cell class: `channel` um between the rows, one ChannelRoute
    #- per crossing net. `routes` says how the pieces are JOINED; it
    #- is the subcell classes above that make the cell assembled
    channel = 8
    routes = [
        {"net": "VCP", "track": 6, "drops": [[n_mirr, "M2", "left"],
                                             [p_bias, "M2", "right"]]},
        {"net": "VS", "track": 14, "layer": "M4",
         "drops": [[r_deg, "M4", "left"]]},
    ]
```

`SidecarCell.compile()` turns the class into the spec dict; the two
recipes that execute it live in `core/sidecarcell.py` and are mixed
into every sidecar cell -- `SidecarPycell`, which places devices, and
`HierPycell`, whose `hierarchy()` splits the cell's netlist and
builds a LayoutCell per subcell before `place()` tiles them.

Which recipe a cell gets is what it HOLDS, not how it was built:
declare subcell classes and the cell is made of SUBCELLS, declare
none and it is made of DEVICES. `routes` decides neither — it says
how the pieces are joined, and an assembled cell may declare
`routes = []`. One object, one pass, one process — there is no
`<CELL>_HIER` scaffold, no generated netlist between two passes and
no role to pass in. Detection is by content: a `<CELL>.py` defining a
`SidecarCell` subclass is the sidecar; a module with module-level
hooks and `data` is a classic pycell, unchanged — the escape hatch
for a cell the recipe cannot say.

The split itself is `core/hierarchy.py`: membership from the
design's own regexes over `ckt.instances`, and a net is a port iff it
is used outside the subcell. Both are properties of the NETLIST, so
they are known before anything is placed — which is what lets a
subcell be BUILT as a cell from its own `Subckt`, from its own
origin, instead of copied out of a placed parent.

Subcell hooks are methods — `beforePlace(self, entry)` /
`beforeRoute(self, entry)`, run between afterPlace and beforeRoute.
There is no class-level `route` hook: `LayoutCell.route()` is a real
method a hook would shadow; claim the subcell by returning True from
`beforeRoute`. A separate `<SUBCELLNAME>.py` beside the design still
works (plain functions `(layout, entry)`, legacy `route` included)
when a subcell's routing outgrows the sidecar file, but the class
hooks win when both exist, and stubs are no longer generated. A
`DiffPair`/`Mirror` declines the built-in series router through its
`routeInternal()` — implementing that method on the class is where a
real diffpair/mirror router will land.

### Paths: the router's conclusions live in the sidecar

The maze router decides; the decision belongs in the design — and it
is stored as a STORY, never as a coordinate. A subcell class declares
its routes as `paths`:

```python
from cicpy.core.path import PITCH, SPACE, pin, track, \
    left_of_pins, right_of_pins, tab_lane

class p_bias(Stack):
    ...
    #- a rail COLLECTS its pins: no start/stop, so a device added to
    #- the column grows the rail with no line changing here
    paths = [
        dict(net="VO", layer="M1",
             steps=[("trunk", right_of_pins())]),
        #- a flyover: ride the tab lane a layer up, touch down only
        #- on your own pins
        dict(net="PWRUP_N_1V8", layer="M4",
             steps=[("trunk", tab_lane()), ("taps",)]),
        #- a two-pin story names its ends
        dict(net="VO1", at="e",
             start=("xload3", "VO1"), stop=("xload5", "VO1"),
             steps=[("up",),
                    ("movex", pin("xload5", "VO1", "x")),
                    ("end",)]),
    ]
    #- and the nets that must NOT be drawn: a supply every source
    #- already reaches through the guard. No geometry, so nothing to
    #- go stale and no fingerprint to guard it.
    blocked = [
        ("VSS", "the guard carries it"),
    ]
```

Every anchor — `pin(...) ± n*PITCH`, `track(channel, i) ± SPACE`,
`right_of_pins()`, `tab_lane()` — recomputes from the pins on every
build, so **a placement change moves the wire instead of invalidating
it**. This replaced the older `wires`/`wires_key` blocks, whose
resolved coordinates were guarded by a placement fingerprint: measured
on LELOTEMP_CMPR, the fingerprint had been stale for days while every
wire replayed anyway — inert in the good case, silently discarding in
the bad one. If you meet a `wires` block in an old design, convert it;
if you meet a bare number, refuse it.

### The loop: search → emit → import → verify → next net

One net at a time, and the search does the discovering while the
design keeps only anchors:

```
1  DECLARE the net as a search:              mazes = [dict(net="X",
   a layer budget and two ends,                layers=("M2","M3","M4"),
   nothing more                                between=[(a,"X"),(b,"X")])]
2  BUILD once (make mag). The search runs, draws what it proved, and
   EMITS the route to <CELL>.routes.py as an anchored `paths` entry —
   every corner resolved to a pin or a channel track. A corner nothing
   reproduces is marked UNANCHORED with the number in a comment: that
   entry is a draft to finish, never a coordinate to inherit.
3  IMPORT: paste the entry into the sidecar's `paths`, delete the
   maze, gate with `paths_only = (..., "X")` while verifying.
4  VERIFY, all four, before the next net:
       make drc  CELL=<CELL>
       make gds kdrc CELL=<CELL>        # gds FIRST or kdrc is stale
       make cdl lvs  CELL=<CELL>        # read only "Final result:"
       make ant  CELL=<CELL>
5  NEXT net. paths_only = None when the cell is done.
```

`paths_only` gates `paths` and `mazes` both — `None` means all, a
tuple names the enabled nets, and an empty tuple draws NOTHING (it is
not "everything"). The search stands aside for any net declared as a
path, so a bisected net stays undrawn rather than quietly searched.

Two rules the emitter enforces so you do not have to:

- **anchors, or refusal.** The emitter's tolerance is a quarter lane
  (the search walks a finer grid than the lanes), and a corner that
  no pin or track explains comes out UNANCHORED, loudly.
- **paste-ready means gated.** Verify the imported story under
  `paths_only` before opening the gate — the search proved the route
  against the metal that existed when it ran, and your paste order is
  not its run order.

### The flow

```bash
cd work
make mag      CELL=X     # ONE command: X's subcells are built, each
                         # written as .mag/.cic/.sch/.sym, and X is
                         # assembled from them
make drc      CELL=X_P_BIAS       # every subcell verifies standalone
make gds cdl lvs CELL=X_P_BIAS    # gds FIRST or extraction is stale
make kdrc     CELL=X_P_BIAS       # klayout reads the flattened gds:
                                  # it catches the partial-overlap and
                                  # sliver classes magic's hierarchy
                                  # tolerates
make drc      CELL=X
make gds cdl lvs kdrc ant CELL=X
```

Read the LVS verdict from the **`Final result:`** line and nowhere
else: netgen prints "Netlists match uniquely **with port errors**" on
*failing* runs, so grepping for "match uniquely" green-lights broken
cells. Measured — a subcell shipped with its ladder unrouted behind
exactly that false positive.

### Stories: how the TOP routes between blocks

`routes:` above is for a cell whose subcells are tiled in rows. A top
level that is a floorplan of finished blocks routes with **stories** --
`layout.path()` -- which say where a net goes as a sequence of moves,
each aimed at a *named* thing rather than a coordinate:

```python
p = layout.path("RST_A", "M2", start=[pin_a], stop=[pin_b])
p.movey(p.track("cband", 8))       # a band track
p.up("M5")                         # change layer
p.movex(p.track("dband", 2))       # a channel lane
p.down("M4")
p.movey(p.landing("y"))            # the stop rect's row
p.up("M5")
p.movex(p.landing("x"))            # ...and its column
p.end()                            # land on it
```

`p.track(channel, n)`, `p.pin(inst, net, axis)` and `p.landing(axis)`
all resolve at draw time, so the story survives a resize. `p.end()`
lands on the stop rect -- never call it on a leg that is meeting a
supply *ring*, because a ring spans the tile and the last leg would run
to the middle of the cell; `movey` to the ring's row and drop a via.

**`CICPY_TRACE=<net>` prints where every step of that net resolved.**
Use it the moment a leg goes somewhere unexpected -- it is the only
thing that shows a lane resolving *outside* its channel. Measured:
`track("dband", 12)` came back 1494800 for a channel ending at 1489800,
so the descent landed inside the neighbouring block and merged four
nets. Nothing in the short report said "your lane index is too big".

### Ask the BLOCK where it is free

A story that crosses a placed block needs a corridor through it, and
the block is what knows -- not the pycell routing over it. `inst.x1 +
40000` is this technology, this floorplan and this day.

```python
ok = layout.addBlockChannel("digfree", dig, "M5",
                            span=(int(pin.y1), int(dig.y2)),
                            near=int(pin.centerX()),
                            net="RST_B")          # <- for THIS net
if ok:
    p.movex(p.track("digfree", 1))
```

It returns the registered `(lo, hi)` or **None**, and a `None` that is
not checked is the expensive kind of bug: every later `p.track("digfree",
n)` then resolves to a bogus x and the leg is drawn somewhere arbitrary.
**Guard the call.** Measured on LELO_TEMP: an unguarded one put RST_B's
descent on top of RST_A, one merged net, and it was the whole LVS
failure.

**`net=` is usually required, not optional.** Without it the question is
net-blind, and a block that routes one of its own nets clear across
itself answers "no corridor" to everybody -- including that net, which
only wants to reach its own pin. `freeColumns` / `freeRows` take it too.
Note that what belongs to a net is more than what is *labelled* with it:
the block view stamps a net on routed metal only, so port rects and via
pads come back unattributed and are claimed by overlap.

When there is no corridor the error names the widest obstacles on the
layer with their nets, and the spans a route of any width could have
used -- "none at all" and "none wide enough" are different faults.
`CICPY_WHYBLOCK=lo:hi` lists every rect in a column with its net.

### ChannelRoutes and drops

Each `hier: routes:` entry lays one full-width bar (a `ChannelRoute`,
default M3) on a named channel track and connects pins to it with
`addRouteConnection` drops. **Drops are discovered**: every placed
subcell whose ports expose the net gets one, using the route-level
defaults (`layer: M2`, `align: center`, `cuts: 2`, pin cut on). The
`drops:` list only *overrides* — `[inst, layer, align, 'nopin']` or
the dict form `{inst:, layer:, align:, cuts:, pin_cut:}` — for the
columns where pins share an x and must split by layer or alignment.
After the drops, the bar is trimmed to its outermost connection and
the port refreshed.

Via and cut behaviour worth knowing (all enforced in cicpy, not in
the design):

- **A lone 1x1 via is the last resort everywhere.** Cut selection
  walks 2x1 → 1x2 → 1x1 and takes the first that fits the target;
  the maze router's via emitter does the same, space-checked at the
  candidate's own extent.
- **The pin cut follows the align**: flush left on `align: left`,
  flush right on `right`, centered and clamped inside the pin
  otherwise. A centered two-cut pad on an aligned drop otherwise
  overhangs the pin into the neighbouring lane (li.3, measured).
- **The rail cut avoids the trunk traffic**: it slides along the
  channel bar away from other nets' drop verticals, within the
  window where its pad still covers the wire.

### Dummies are supply devices

A fill transistor shorts to its stack's supply -- PMOS dummies to
VDD, NMOS dummies to VSS -- in three places that must agree:

- the **hand schematic** carries one fill instance per device class
  with every pin on the supply (lowercase `xfill_*` names);
- the **generated subcell netlists** emit each fill with all
  terminals on the stack's supply;
- the **layout** straps the fill's D/G/S and ties the strap into the
  adjacent tap row.

The floorplan consequence: fills go at the **bottom** of a column,
below every pin span. A supply-tied bar inside a rail's span blocks
the lane -- measured, a drain net degraded to an M2 rail whose via
pads then blocked the gate-tab lane.

### Trunks come from pins, never from coordinates

`trunkx` is the resolved form the tools emit; a design never writes
it. Stack pycells state their rails with the pin-relative options:

- `trunkright` -- the pins' common overlap, right edge: the
  rightmost trunk that still lies on every pin (a short bar narrows
  it for everyone, which is the point);
- `trunkleft` -- the same from the left;
- `trunktab` -- centred on the rightmost narrow (<=4 um) rect, the
  gate-tab lane; rightmost because duplicate subports plant false
  tabs to the left.

They resolve against the route's collected rects at draw time, so
the same pycell survives a resize untouched -- verified when the OTA
went from 6 to 4 input devices and every hand rail followed.

### Conventions that are load-bearing

- **Schematic instance names are lowercase.** The netlist keeps the
  name verbatim; `name=Xxfill_...` reached the tools as `xxfill_...`,
  slipped past every `xfill_` check, and published two phantom
  subcells at the origin on top of a device row. The `xfill_` prefix
  is reserved for fill devices (layout-generated dummies and their
  schematic LVS counterparts).
- **Stack order is placement**: the `order:` list is bottom-to-top,
  and it is where tab-lane conflicts are solved. An N stack puts its
  gate device (`xns*`) at the BOTTOM so the tab-lane rail spans the
  rows above it; interleaved gate tabs in one 3.2 um lane are
  unroutable at any layer pair.
- **Published subcells keep parent-absolute coordinates**; the
  assembly cancels them per instance (`xcell = -sub.x1`). The publish
  frame shifts whenever flat content changes, which makes every .mag
  diff 100% churn — diff geometry normalized by the label shift, not
  line by line.
- Design pycells import publication helpers from
  `cicpy.core.subcell` (a compat forward from `mazerouter` exists,
  because a failed pycell import is swallowed and the stack silently
  publishes without its routes).

## The loop

Layout is an iteration, not a single generation. Every change goes through
the same cycle, and the two verification steps are not optional:

```bash
cd work
cicpy sch2mag <LIB> <CELL>          # generate placement from schematic
make drc CELL=<CELL>                # let the design rules judge it
cicpy svg ../design/<LIB>/<CELL>.cic <tech> <CELL> --I <libs...>
                                    # render it and LOOK at it
```

Routing has a stricter loop: **one route, one check**. Run
`cicpy sch2mag --strict <LIB> <CELL>` and the flow checks connectivity
after every route, stopping at the first one that creates a short, with
the command and file:line in the error. It also refuses to route at all
while the placement itself is shorted. The `connectivity` MCP tool runs
the same check on demand and lists every short and open with route
attribution.

Rules that follow from the loop:

- **Never guess spacing.** Design rules are not monotonic in distance:
  a gap that is too small for one rule can be too large for another, and
  the clean values are found empirically. Change one spacing, rerun DRC,
  read the rule names it prints.
- **Look at the picture.** DRC counts do not show a stack placed in the
  wrong row, a floating strap, or a hole in a guard ring. The SVG does.
- **Do not route before placement is DRC clean.** Routing on top of a
  dirty placement mixes two error sources.

### Reading the SVG

`cicpy svg` writes `<CELL>_svg/<CELL>.svg`. Two things to know:

- The SVG y axis points **down**, layout y points **up**. The pmos row you
  placed on top renders at the bottom of the image. When identifying a
  stack in the picture, confirm against coordinates from the mag file
  before acting on it.
- Convert to a raster to inspect
  (`rsvg-convert -h 1200 -b white cell.svg -o cell.png`), and crop the
  region you care about rather than squinting at the whole cell.

### Locating DRC errors

`make drc` prints rule names and a count. To get coordinates, step through
the errors in magic:

```tcl
load ../design/<LIB>/<CELL>.mag
set b [view bbox]
box values [lindex $b 0] [lindex $b 1] [lindex $b 2] [lindex $b 3]
expand
drc style drc(full)
drc catchup
drc find
puts "ERRORBOX [box values]"
drc why
```

The reported coordinates are in magic internal units, which are the mag
file units times two.

## Read the netlist before grouping

Placement groups come from schematic instance names, but the grouping
must follow the **circuit**, not the names as they happen to be. Netlist
the cell and read the connectivity: which devices share a source node,
which are the matched pair, which are powerdown pulls. Name collisions
(a bussed `xa1[3:0]` next to a scalar `xa1`) and devices that ended up in
the wrong group are common in schematics that have been edited a lot.
Rename instances in the schematic until every group is one function.

Conventions:

- The group name of an instance is the leading letters of its name:
  `^(x\D+)` — `xbl0<2>` and `xbl5` are both group `xbl`, and `xd2` is
  group `xd`, not `xd2`.
- **A group holds devices of one width only.** Stacks place devices on a
  shared column, mixed widths do not stack.
- Give matched devices one group and split them in the layout script,
  do not scatter them over groups.

## Placement API, in the order you use it

```python
def afterPlace(layout):
    grp = layout.makeCellGroup("pmos")
    a = grp.addStackByGroup("xbl", name="p_in")          # whole group
    b = grp.addStack("p_in_b", instances, preserveOrder=True)  # explicit slice

    for s in (a, b):
        s.stack()          # REQUIRED after slicing: packs the column,
                           # split stacks inherit interleaved positions
                           # from their source group and have holes

    grp.fillDummyTransistors()   # fill short columns to the tallest,
                                 # with dummies of each column's own device
    a.addTaps()                  # tap cells above and below the column
    b.mirror()                   # mirror a matched half about its axis

    b.abutRight(a)               # A.abutRight(B): A moves to the right of
                                 # B, bottoms aligned. abutTop: A above B,
                                 # lefts aligned.
    grp.updateBoundingRect()     # after moving stacks, before group abuts
    grp2.abutTop(grp, space=...)

    grp.routeDummyDevices()      # M1 strap across each filler

    layout._route_scopes = {"p_in": a, ...}   # hand stacks to beforeRoute
```

Facts that are not obvious from the signatures:

- `addStackByGroup` does not compact. The first pass drops devices on the
  routing grid and a stack keeps those positions; call `stack()` when you
  build stacks from slices.
- `addTaps` derives the tap cell name from the device name
  (`..._12C5F0` becomes `..._12CTAPBOT/TOP`). Device variants like LVT
  have no tap counterpart, the plain tap of the same width class is used
  automatically. If no tap exists at all the stack warns and stays
  untapped — treat that warning as an error.
- `mirror()` is for matched pairs: mirror the right half, then abut it
  against the left half. The seam then has mirror symmetric edge
  geometry, which is allowed to abut where two identical columns are not.
- Dummies are created by `fillDummyTransistors` as `xfill_<stack>_<n>`
  physical instances of the column's base device. They are not in the
  netlist and get an M1 strap from `routeDummyDevices`.
- Group `abutTop/abutRight` moves the whole group. Its bounding box comes
  from its stacks, so anything you forgot to put in a group does not move
  with it and anything misplaced inside stretches the box.

## Spacing facts, sky130

Found empirically, verified by DRC. Units below are cicpy layout units
where 200 units = 1 um.

| boundary | spacing | why |
| :--- | :--- | :--- |
| pmos stack to pmos stack | **abut, 0** | the n-wells must merge. Any small gap puts two well edges inside the 1.27 um nwell spacing (nwell.2a); the well reaches ~1.5 um beyond the stack box, so "a bit of margin" is the worst choice |
| nmos stack to nmos stack | **2 um (400)** | abutting violates licon spacing across the seam and magic refuses subcell abutment on locali; gaps of 0.3 to 1.5 um each trip a different tap or diffusion rule. 2 um is the smallest clean value found |
| mirrored matched halves | **abut, 0** | mirror symmetric seam geometry, works for both nmos and pmos pairs |
| poly resistor to anything | **2 um (400)** | poly.9 wants 0.48 um from resistor poly to any diffusion or poly, and the resistor guard adds its own tap rules |
| pmos row to nmos row | 2 um (400) | well edge to nmos diffusion |

## Geometry model

- A cell's **FIXED_BBOX is the abutment box**, deliberately smaller than
  the drawn content. Stacked devices overlap: content overhangs the box
  and neighbouring rows share their boundary geometry. Placement,
  pitches and abutment all work on this box. Do not "fix" a cell whose
  drawing is bigger than its box, that is the design.
- The vertical pitch inside a stack equals the box height (800 units,
  4 um for the standard cells). The visible gap between the drawn devices
  is the **horizontal routing channel**, not wasted space — finished
  cells fill it with M2/M3 routes.
- Everything in a `.cic` file is in database units (100 units = 5 nm);
  mag files written by cicpy are `magscale 1 2`. If you hand-compute
  coordinates across files, check units against a cell of known size
  first.

## Routing

The route language is shared with the compiler; the full reference is in
[routes](routes.md). The short version an agent needs:

**Directed routes** (`addDirectedRoutes` in json,
`layout.addDirectedRoute` in python): `["layer", "net",
"START<type>STOP", "options"]` where START/STOP are instance:terminal
regexes and `<type>` is drawn with dashes and pipes:

| type | meaning |
| :--- | :--- |
| `-\|--` | left: horizontal, vertical, horizontal, cuts left aligned |
| `--\|-` | right: same, cuts right aligned |
| `-` , `->` | straight horizontal |
| `\|\|` | straight vertical |
| `-\|` / `\|-` | U shapes right / left |
| `--\|` / `\|--` | U shapes top / bottom |
| `-\|-` | no alignment of its own, the options decide (`straight`, `strap`, ...) |
| `>-\|--` | left with the start offset low one routing width |

Common options: `straight`, `strap`, `leftdownleftup`, `leftupleftdown`,
`offsetlow`, `offsethigh` (+`end` variants), `2cuts`, `2vcuts`,
`cutalignright`, `noport`, `onTop`, `routingWidth<n>`.

**Connectivity routes** (`addOrthogonalConnectivityRoute(vertLayer,
horizLayer, netRegex, options, cuts)`): routes a whole net using the
access geometry the devices already expose. Options place the horizontal
bar: `track<n>` counts routing tracks (negative counts from the other
side), `onTopLeft`/`onTopRight`/`onTopB` pick the attachment side.
Pin geometry comes from the port's own layer; `accessLayer=X` in the
options attaches at a pin's same-net metal on X instead of stacking
from the pin layer.

**Power and ports**, the pattern from a finished cell:

```python
def beforeRoute(layout):
    layout.addRouteRing("M1", "VDD_1V8", "t", widthmult=3, spacemult=2)
    layout.addRouteRing("M1", "VSS", "b", widthmult=3, spacemult=2)
    layout.addPowerConnection("VDD_1V8", "", "top")
    layout.addPowerConnection("VSS", "", "bottom")
    scope = layout._route_scopes["p_in"]      # stack-local routes first
    scope.addOrthogonalConnectivityRoute("M2", "M3", "^IBP$", "track-2,onTopLeft", 1)
    layout.addOrthogonalConnectivityRoute("M4", "M3", "^VO$", "onTopLeft,track4", 1, "", "")

def afterPorts(layout):
    layout.addPortOnEdge("M2", "VO", "top", "||", "")
    layout.addPortOnEdge("M3", "IBP", "left", "|-", "track0")
```

Route debugging: `sch2mag` prints a route short report naming the shorted
nets and the python callsite that drew the offending route. For opens and
split nets run `sch2mag --check-connectivity`, it is slower and not the
default loop.

## Supplies go to the guard, not up a strap

**Do not call `addPowerConnection` on a library whose pins overhang
their abutment box.** It copies the PIN rectangle and stretches it to
the ring *on the pin's own layer*, so the source of an upper device
drags that layer down across the drain and gate of everything below
it. On REY_ATR it shorted every signal in a cell to a supply. Measured
on LELOTEMP_CMPR, on the BARE PLACEMENT with not one signal route
anywhere in the cell, `checkroutes` reported two components of 31
rects each:

    VBN1,VBP2,VDD_1V8,VIN,VIP,VO,VO1,VS
    IBP_1U,VBN1,VBP2,VIP,VO,VO1,VSS

JNW_ATR's 2.56 um cells do not overhang, which is why the older
designs got away with it and why the failure looks like a routing bug
in a cell that has no routes.

The pair to call instead, and what each is for:

    layout.addRouteRing("M1", net, side, widthmult=3, spacemult=2)
    layout.addPowerGuardConnection(net)
    layout.addPowerStrap(net, "", side, terminals=("B",))

`addPowerGuardConnection` is the whole connection for a library that
rings each device in its own tap: the source sits a fraction of a
micron from the guard column beside it, on the same layer, and the tap
cells already tie the guard up, down and across. So it is a jog at the
device's own row instead of a rail the height of the column, and every
layer above stays empty for signals. `addPowerStrap` then carries only
the BULK terminal out to the ring, one routing width wide rather than
one pin wide, with the via down on the pin.

**The stack's own M1 supply routing stays.** What is wrong is
`addPowerConnection`, which reaches across the cell on the pin's
layer; the local M1 tie inside a stack is the connection you want and
`routeParallel`/`routeMirror` keep making it. Do not "fix" a supply
short by taking the supply out of the stack -- that removes the right
connection along with the wrong one.

### checkroutes used to read ONE .cic and nothing else

A `.cic` records a device instance as **four Port rects and a
reference**; the cell's own metal stays in the LIBRARY, and the library is a
different repo reached through a symlink. So a checker reading only
the design's own `.cic` saw ~4 rects where the cell has ~40, and
anything a route collided with that was not one of those four was
invisible.

The library's `.cic` was there the whole time --
`rey_atr_sky130a/design/REY_ATR_SKY130A.cic`, 210 cells. What made it
easy to miss is where it sits: `design/REY_ATR_SKY130A` in the design
repo is a symlink to the library repo's *directory*, and the `.cic`
holding the cells is BESIDE that directory, named after it, one level
up from where the symlink lands. Resolve the symlink and it is one
join away -- which is what `_libraryCandidates` now does.

Measured on LELOTEMP_CMPR's `n_mirr_load`: `checkroutes` reported
**0 shorts** while the extracted netlist had three nets merged into
VSS. The cause was an M2 rail lying on the M1 tab column that every
cell in the library carries and no `.cic` mentions. The same blindness
invented OPENS -- VSS came back "split into 8 components" because the
metal joining those pieces lives inside the cells.

`Design.loadMissingFromLibraries` now loads them automatically: the
instance already records `libpath`, so nothing has to be passed on the
command line and the blind configuration is not reachable by
forgetting a flag. What that
changed, same layouts, before -> after:

| cell | before | after |
| :--- | :--- | :--- |
| LELOTEMP_CMP | 0 shorts 0 opens | 0 shorts 0 opens |
| LELOTEMP_OTAR | 0 / 9 | 0 / **2** |
| LELOTEMP_BIAS_IBP | 3 / 7 | 3 / **4** |
| LELOTEMP_CCMP | 4 / 3 | 4 / **1** |
| LELOTEMP_CMPR | 1 / 10 | **1** / **0** |
| ..._N_MIRR_LOAD | **0** / 3 | **1** / **0** |

Most of the opens were never real, and one short was. Shape counts
went up 10x to 50x; that is the geometry the checker had been ignoring.

Two rules follow:

- **A "0 shorts" beside a split supply is not a result.** If the
  checker also reports the supply in N components, it is not modelling
  the cells, and it cannot see anything merging INTO a net it has
  already fragmented.
- **Compare shape counts when a checker surprises you.** 41 shapes for
  an eight-device column is the tell that the library is missing;
  873 is the real number.

**Check the placement for shorts before you route.** One
`checkroutes` on the bare placement is seconds and it is the only
moment when a short can only be the placement's. Everything after it
is two error sources mixed.

## Look before you route

A track number is an *offset from the net's own pins*:

    trunk_x = anchor_right + (track + 1) * vspace + track * vwidth
    base_y  = min(rect.centerY() for rect in self.accessRects)

so two nets whose pins share a column compute nearly the same anchor and
land on each other at the same track number, and neither can tell. The
only way to discover that from the route language is to draw it and read
the short report, which costs a full regeneration per guess. Do not
route that way. Ask first:

    cicpy tracks <cic> <tech> <cell> --layer M3
    cicpy tracks <cic> <tech> <cell> --layer M3 --band 279000:363000
    cicpy tracks <cic> <tech> <cell> --layer M4 --free 217000:609000

The MCP tool `tracks` is the same thing. `--free LO:HI` is usually the
question you actually have: a track carrying a short wire at one end is
still usable at the other, so whole-empty tracks understate the budget.

This is worth doing before the first route, not after the first short.
LELOTEMP_OTAR spent an evening at six opens with every horizontal bar
fighting inside the device rows, and one query showed why: the 84 um
channel the placement had opened between the rows held 21 M3 tracks and
all 21 were free. Nothing ever sent a bar there, because `base_y` comes
from the net's own pins.

## Aim at a channel, never at a coordinate

Register the gaps the placement makes, then route to them by name and
index. In `afterPlace`:

    layout.addRoutingChannel("mid", nmos.y2, pmos.y1)
    layout.addRoutingChannel("bias", p_bias.x1, p_bias.x2, horizontal=False)

and in `beforeRoute`:

    layout.addOrthogonalConnectivityRoute(
        "M4", "M3", "^VO$", "hchannel=mid,htrack=5,vchannel=bias,vtrack=8",
        1, "", "")

`hchannel`/`htrack` place the horizontal bar, `vchannel`/`vtrack` the
trunk, and both may appear together. The registration holds the only
numbers and they come from the placement that just ran, so the cell
still moves to another technology and survives a resize.

Never write `bandy`/`trunkx` in a design. They exist as the resolved
form of the above and a coordinate in a pycell outlives nothing.

## Ask before you draw

Three questions, each answerable without a regeneration. The old loop --
draw a guess, rebuild, read the short report -- costs a full rebuild per
guess, and five of them were spent on one net before any of these
existed.

    tracks     which corridor is free, and where
    blockers   what stops THIS net from dropping a via column HERE
    findroute  is there a way through at all, and what does it cost

`blockers` is the one that is not obvious. When a route shorts and the
track report looks clean, the collision is almost never on one layer: a
trunk on M4 and a pin on M1 never share a track, so a same-layer check
reports nothing. What collides is the via COLUMN -- a route reaching a
pin comes down through every layer at that x, and any other net's pin in
the way is shorted. Every routing failure measured in LELOTEMP_OTAR was
that, four separate times.

Two facts that fall out of it and are worth carrying:

- **Ask the technology for the via size, never assume it.** The sky130
  1x1 cut is 4000 square. A guess of 8800, carried over from a note about
  pad clashes, made the router declare every ladder net in
  LELOTEMP_OTAR unroutable: it could not leave a pin, because it believed
  a pad centred on one terminal covered the neighbour 4000 away.
  `Cut.getInstance(a, b, 1, 1).width()` is the answer.
- **A via occupies only the layers it connects.** A whole descent from M4
  down to a pin passes through everything on the way; one M1->M2 step
  does not. Treating a single via as claiming the full column makes it
  illegal to via beneath any unrelated upper-layer wire, which is not a
  short in any technology.
- **Bars land where the pins are, not where there is room.** A plain
  route takes its bar height from the net's own pins, so bars fight
  inside device rows while the channel between them sits empty.
  Measured: one bar inside the pmos row with 27 free M3 tracks in the
  channel it should have used.

## Router facts that cost a day to learn

- **One net per row channel, unless you place them.** The router lays a
  horizontal bar per device row and puts every bar of a channel at the
  same height; the plain `track` option does not separate them, because
  it is relative to each net's own pins. Two nets whose bars share a row
  channel with overlapping x short. Either keep nets column local
  (vertical bundle rails via routeDiodeConnected/routeMirror), or give
  the crossing ones a named channel track each, which is what the
  channel is for.
- **routeMirror rails do not stagger.** A column with several nets on
  the same terminal puts all their rails on the same x. Until the router
  staggers rails, such columns cannot be bundle routed.
- **Series chains cannot overlap stack.** The transistor cells carry
  full height M2 rails, and at the overlap pitch neighbouring cells
  merge them, which shorts a ladder end to end. DRC does not see it,
  the connectivity check does.
- **Meet a pin on the metal it has already been brought up to.** A pin
  usually arrives with its own via under it, and a SUBCELL's route may
  have taken its port a layer higher still. Drive a stack all the way
  down to the pin's layer and it lands a second via on the first --
  concentric but not identical, tens of nanometres apart, which magic
  reports as

      This layer can't abut or partially overlap between subcells

  and which no amount of moving the ROUTE will fix, because the route
  is not what is wrong. Say where the stack lands:
  `endStopLayerM2` in a route's options,
  `promoteInstancePort(..., stopLayer="M2")` on a riser. Measured on
  LELOTEMP_BIAS_IBP: 8 errors to 0, and one via and one pad fewer.

  A hint on where to look: when magic complains and klayout's deck does
  not, suspect a HIERARCHY rule like this one rather than a spacing
  rule, and go straight to the cut layers.

### Read the BRIDGE lines, not the track map

`checkroutes` names the exact pair of shapes that merged:

    BRIDGE VIP|VS: M3 (183200,240100)-(246900,243100) [VIP]
                   touches VIA2 (215800,241400)-(218600,244200)
                   [cut_M1M4_2x1]

Every short measured in LELOTEMP_CMPR looked like that -- a bar
through somebody's via COLUMN, or a rail sitting on a foreign pin --
and **not one was two wires crossing on a layer**. The track maps
stayed clean the whole time the cell was shorted, because a track map
answers "what else is on this layer at this coordinate" and that was
never the question.

Two habits follow:

- **Bisect with a per-net switch.** A three-line harness in the
  sidecar (`CMPR_ONLY="VBN1,VS"` builds only those routes) attributes
  a short in one build instead of five. Its most useful result on
  CMPR: no PAIR of the four M4 nets shorted, but any THREE did --
  which is the signature of a via column, not of a wire.
- **Naming the trunk is half a route.** `vchannel` alone leaves the
  bar wherever the net's own pins put it, and a bar leaving lane 0
  rightwards runs straight through the trunks in lanes 1 and 2 (16
  measured VBN1 x VO1 pairs). Name `hchannel`/`htrack` too, so the
  two indices make each crossing a single point of one layer over
  another.

### A via pad is taller than a lane

A lane is width+space, 0.6 um on sky130 metal; a via pad is 0.88 um.
So a device row is *not* six free lanes when two nets share it -- it
is however many the pads leave. Measured: VO1's bar at r5 track 4
landed inside VBN1's gate pad on `xn_mirr_load3`, the one device that
carries both nets.

### A rail on the pins cannot be moved by a channel

A net with a pin on several rows of one column gets a vertical down
that terminal's lane whatever the trunk option says -- the trunk is
where the net *stands*, the rail is where its *pins* are. VBP2 has a
pin on every row of `p_mirr_tail`, so it laid M2
(304900,60700)-(307900,366300) down the whole column with two other
nets' drain stacks inside it, and no lane assignment could help. The
fixes that do work are a different lane **on the pin layer**
(`trunktab`, the gate-tab lane, which is what `routeMirror` and
LELOTEMP_OTAR's `p_bias` use) or a layer change.

And check the rail's ends: excluding one device is often the whole
fix. That tab rail then landed on the one device in the column whose
gate is a different net, a 6-rect PWRUP_1V8|VBP2 component; excluding
it and picking its drain up separately closed it.

### A port leaves on the layer its net is routed on

`addPortOnEdge` draws a bare run from the port rect to the edge on the
layer it is given and adds **no via** to whatever the net is actually
built from. Ask for M2 on a net with an M4 trunk and you get a riser
lying beside its own net, touching nothing: VIP came out M2
(121300,2000)-(124300,139000) with its M4 rail at 124900. netgen says
it as "Top level cell failed pin matching", and magic says it more
plainly in the extraction log -- `Ports "A" and "B" are electrically
shorted` is worth grepping for after every run.

### netgen's net count means nothing if pin matching failed

A run that prints

    Circuit 1 contains 13 nets, Circuit 2 contains 13 nets
    Final result: Top level cell failed pin matching

has **not** compared the connectivity -- it bailed at the ports. Do
not read matching counts there as evidence that a `checkroutes` short
was a false positive. Measured: it was real, and magic's extraction
log named the same three nets.

### Attaching one net group by group

`addChannelConnection(vLayer, hLayer, regex, channel, track, ...)`
exists for the net that has to be picked up in two places: successive
calls for the same net on the same channel track extend ONE shared bar
across the union of their spans. Two plain orthogonal routes each draw
a bar over their own pins and meet only if those spans happen to
overlap -- measured, a bias-side bar 0.88 um wide in a 34 um cell,
with the net in four components.

### A port in the middle of a block cannot be left

A port the parent has to *reach* must be somewhere the parent can get
to: an edge, or metal high enough to fly over what is in the way. Left
mid-row, the router climbs the block to find it, and climbing means M4
or M5 across everything the block owns up there -- a 72 um M4 riser
straight through a MiM cap bank, in the measured case.

The fix is an **edge port**: make a pad at the edge in the ROUTING
phase, path to it, and name it in `afterPorts`.

```python
def _crossings(self, layout):
    from cicpy.core.rect import Rect as _Rect
    self._edge_ports = {}
    for net, layer, xlane, edge in self._EDGE_PORTS:
        r = self._port(inst, net)
        x = int(inst.x1) + xlane
        y = int(layout.y1) if edge == "bottom" else int(layout.y2) - 4000
        pad = _Rect(layer, x, y, 3200, 4000)
        pad.setNet(net)
        layout.add(pad)
        p = layout.path(net, "M1", start=[r], stop=[pad],
                        options="1cuts,2vcuts")
        p.start(); p.up(); p.up()        #- M2, then M3 across
        p.movex(p.landing("x"))
        p.down()                         #- M2, and down the lane
        p.movey(p.landing("y"))
        p.end()
        self._edge_ports[net] = pad

def afterPorts(self, layout):
    super().afterPorts(layout)
    for net, pad in self._edge_ports.items():
        layout.updatePort(net, pad, routeLayer=pad.layer)
```

Both halves matter. **A path created in `afterPorts` never routes** --
the phase is over, and the port comes out as a rect with nothing under
it. And `afterPorts` must not *compute* the pad either: a pad derived
from a story's `endsAt` matched nothing at all in netgen.

### Which edge is decided by the mirror, not by the pin

When the parent stacks two copies and mirrors the upper one `MX`, the
two **top** edges meet at the seam and the two **bottom** edges become
the pair's outer faces. So the edge to choose follows the net, not the
geometry:

| the net is | put it on | because |
|---|---|---|
| shared between the halves | the top edge | the two pads come out adjacent at the seam and abut with nothing drawn |
| per-half (`RST_A`/`RST_B`) | the bottom edge | the outer face is the only place the level above can still see it |

Getting this right deletes seam stories rather than rewriting them.
Three went in one edit, and `_emptyColumn` -- a heuristic that read
the cap bank as the block's right wall -- went with them.

### A pin can be too small for the parent's via

A pin 3200 x 4000 is smaller than every M1M2 cut in one direction:
`1cuts,2vcuts` overhangs 4400 in y, the default `2cuts,1vcuts`
overhangs 5200 in x. The child can land on it because the child knows
what is beside it; the **parent** cannot, and its pad falls on the
neighbouring device's M1. Nothing is wrong in the child -- 0 DRC,
shorts=0 -- and LVS at the top says the pin is tied to a source.

Lift it **in place**: make the cut in the child, publish the port on
the M3 above it, and let the parent arrive on metal with room around
it. In place, not at an edge -- a port list the parent depends on does
not move.

```python
pad = _Rect("M3", ..., w, 4000)
p = layout.path(net, "M1", start=[r], stop=[pad], options="1cuts,2vcuts")
p.start(); p.up(); p.up(); p.end()
layout.add(pad)
layout.updatePort(net, pad, routeLayer=pad.layer)   #- in afterPorts
```

Size the pad off the **pin**, with a floor for the narrow ones:
`w = max(8000, pin.x2 - pin.x1)`. A fixed 8000 stub beside a
16000-wide bar runs met2.2 against the block's own M3.

And this symptom has a twin that is NOT the same bug. If the pin is
already wide -- a 16000 bar -- and the parent's pad still lands on a
neighbour, look at *where*: a pad 2900 below the bar, overlapping by
300, is the parent aiming low, not the pin being too small. Lifting
that one only moves the fault.

### Match the child's cut ORIENTATION at a shared pin

`cut_M1M4_1x2` (one wide, two tall) and `cut_M1M4_2x1` at the same pin
overlap *partially*, and that is precisely what magic means by "this
layer can't abut or partially overlap between subcells". It is a
hierarchy rule, not a spacing one, and no amount of moving fixes it.
Read the cut the child used and ask for the same shape.

Rule of thumb: `1cuts,2vcuts` for a gate tab, the default for a wide
bar.

### Detour, do not climb

A net that has to cross a row of cells has two ways past: up to a free
layer, or sideways by a whole PITCH to a row that is free. Prefer the
detour. Climbing to M5 costs a via stack at both ends and M5 costs 1000
in the router's own cost table; a `+ 3 * q.PITCH` offset on the row
costs nothing and keeps the net on M2/M3. Seven crossings in
LELOTEMP_CMPR came out with no M5 at all on offsets of -1, +1 and +3.

Also: when a story steps between layers, work out the direction rather
than assuming.

```python
step = q.up if x > v else q.down
back = q.down if x > v else q.up
for _ in range(abs(x - v)): step()
```

`range(x - v)` silently does nothing when the crossing layer is below
the vertical one, and the net then runs along its neighbour's rail
with no error printed anywhere.

### A step takes something named in the design, never a coordinate

The same rule as *Aim at a channel, never at a coordinate* above, now
enforced: `p.movex(66000)` is rejected outright. Register the column as a channel and ask
for its track:

```python
lay.addRoutingChannel(net, x0, x0 + 12000, horizontal=False)
...
p.movex(p.track(net, 0))
```

### `channel` is two different knobs

`place = {"channel": N}` is the FLAT recipe's. A hierarchical cell --
one with `rows` -- is placed by `placeHier`, which reads a **class
level** `channel` attribute and defaults to 8 um:

```python
class MYCELL(SidecarCell):
    rows = [[caps], [core]]
    channel = 2          #- um between the rows
```

Setting `place["channel"]` on such a cell changes nothing at all, and
the rows stay 8 um apart while you sweep it.

### The .subckt line wraps at 80 columns

Grepping the extracted netlist for a port and reading only the first
line of `.subckt` is how a working approach gets reverted. Two ports
looked missing, and the pin table said "Cell pin lists are equivalent"
the whole time. Read the **pin table**.

## Verification beyond DRC

**LVS is the verdict. `checkroutes` is a lead.** Take that literally:
`make gds cdl lvs` and the `Final result:` line decide whether a cell is
right. Everything below is for finding *where* to look, faster than a
full run.

`cicpy checkroutes <cic> <tech> <cell>` reports shorts and opens from a
.cic that is already on disk, in about a second and without touching a
file. Use it after every routing change. The MCP `connectivity` tool
re-runs sch2mag, which *replaces* the layout it is asked about: right
for an sch2mag design, wrong for a ciccreator library, and it will
overwrite the .mag you were checking.

Two ways it reports a short that is not one, both measured:

- **it flattens, and subcells reuse net names.** `VO`, `VIN`, `LPI` are
  internal to more than one block, and one component carrying two of
  them reads as a short. LELO_TEMP reported 13 shorts on a layout netgen
  called free of them.
- **a bus member is not its bus.** `nets=IBP_1U,IBP_1U<3>` is naming,
  not geometry. So is a port name sitting on the internal net it
  publishes (`nets=CMPO,VO`).

**Check the techfile path before believing any of it.** It is
`<ip>/tech/cic/<techlib>.tech` -- `tech/` is a directory of tooling, not
of tech files. Given a path that does not exist, `checkroutes` used to
answer "0 shorts, 0 opens, clean" for a cell with 12 shorts, 8 opens and
a failing LVS. The MCP tool refuses the run now, but the lesson
generalises: a green result from a tool that should have failed is worse
than no result.

A tap-less leaf cell reports its supply rails split. That is the library
design, not a defect.

**And a DRC improvement can be a short.** Never sweep a placement
parameter on the DRC count alone. Measured, moving one net's lane:

| lane | DRC | LVS |
| :--- | :--- | :--- |
| 9 | 2 | merged into VDD_1V8 |
| 10 | 4 | nothing merged — the right one |
| 11 | 2 | merged with RST_A |
| 12 | 0 | merged with RST_A |

The correct lane was the worst of the four by DRC. Metal that has moved
onto another net is *invisible* to DRC; only LVS sees it.

- `make gds cdl lvs` is the full check; LVS needs the gds regenerated
  first or the extraction runs against a stale state and the result is
  meaningless.
- DRC cannot see shorts. Restored or added metal that crosses another
  net is invisible to DRC and only LVS catches it.

### Finding out WHAT a DRC error is standing on

magic names the rule and not the geometry, and its own queries are no
help without a display: `what`, `what -list` and `select area` all
return nothing under `-dnull`. Two commands answer it anyway, and
neither needs a screen.

Ask magic for the error BOXES:

    load ../design/<LIB>/<CELL>.mag
    box values <bbox> ; expand ; expand
    drc style drc(full) ; drc catchup
    drc listall why        # {rule {box box ...}}

then ask klayout what is inside each box, WITH THE CELL EACH SHAPE
COMES FROM -- which is the part that actually identifies the error:

    it = top.begin_shapes_rec_touching(layer_index, box)
    # ... it.cell().name and it.shape() transformed by it.trans()

The originating cell is the whole answer for any hierarchy rule: two
shapes at the same place mean nothing until you know that one belongs
to the parent and the other to a subcell. Coordinates in a `.mag` file
are cicpy/50; `drc` reports internal units, 0.005 um each in sky130.

And when a rule fires, check the clean cells for the same pattern
before believing your explanation. The first diagnosis of the cut
overlap above was "contacts overlap across cells" -- which happens
~100 times in each of three cells that are 0 DRC. Only the same-LAYER
overlaps tracked the errors. One sweep over four cells cost a minute
and killed a wrong theory that would have moved a hundred innocent
vias.

## Worked examples

In `lelo_temp_sky130a/design/LELO_TEMP_SKY130A/`:

- **`LELOTEMP_CMPR.py`** is the reference for a cell whose routing is
  entirely declared: every column rail, flyover and two-pin story is a
  `paths` entry, the supplies are `blocked`, and there is not a
  coordinate in the file. Its docstring carries the measurements that
  justified each choice — read those before inventing your own.
- **`LELO_TEMP.py`** is the reference for a top: stories through named
  bands, channels registered from the placement in `afterPlace`, a
  corridor measured off a block's own view (`pband`), and `paths_only`
  as the bisect gate.
- `LELOTEMP_OTA.py` still exercises the placement half: netlist-driven
  grouping with renames, folding into mirrored halves, dummy fill and
  tap fallback.
