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

## The sidecar flow — the current best method

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
    #- per crossing net; presence of `routes` enables the hier build
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

Which recipe a cell gets is what it DECLARES, not how it was built:
declare `routes` and the cell is made of SUBCELLS, otherwise it is
made of DEVICES. One object, one pass, one process — there is no
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

### Wires: the router's conclusions live in the sidecar

The maze router decides; the decision belongs in the design. A
subcell class declares its stack-level routes as

```python
class p_bias(Stack):
    ...
    wires = [
        ("VO", "M1", "||", "trunkx=304100"),
        ("VBP", "blocked", "path is not a shape route.py can draw"),
    ]
    wires_key = "6485b44f0f02"
```

each 4-tuple ordinary `addConnectivityRoute` arguments -- edit them
like any other route -- and a `("net", "blocked", reason)` triple a
net the search proved unroutable, replayed as blocked rather than
quietly retried. Declared nets REPLAY: no track map, no A* search,
which are the whole cost of the flat build (measured: 74 s to 0.5 s
on LELOTEMP_BIAS_IBP, 15 s to 0.5 s on LELOTEMP_OTAR, outputs byte
identical). route.py still redraws under whatever the technology
says today.

The options are RESOLVED -- a trunkx is a coordinate -- so
`wires_key` fingerprints the stack's own instances, and any
placement change makes the block stale: the router says so, ignores
it, searches afresh, and writes every searched stack's conclusions
to `<CELL>.routes.py` beside the design as a paste-ready block. The
loop is: build once, read `<CELL>.routes.py`, paste the blocks into
the sidecar, build again. Undeclared nets always search, so a wires
block may cover a stack partially. CICPY_NO_ROUTEPLAN=1 ignores
every declaration.

### The flow

```bash
cd work
make mag      CELL=X     # ONE command: X's subcells are built, each
                         # written as .mag/.cic/.sch/.sym, and X is
                         # assembled from them
make drc      CELL=X_P_BIAS       # every subcell verifies standalone
make gds cdl lvs CELL=X_P_BIAS    # gds FIRST or extraction is stale
make drc      CELL=X
make gds cdl lvs CELL=X
```

Read the LVS verdict from the **`Final result:`** line and nowhere
else: netgen prints "Netlists match uniquely **with port errors**" on
*failing* runs, so grepping for "match uniquely" green-lights broken
cells. Measured — a subcell shipped with its ladder unrouted behind
exactly that false positive.

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

## Verification beyond DRC

`cicpy checkroutes <cic> <tech> <cell>` reports shorts and opens from a
.cic that is already on disk, in about a second and without touching a
file. Use it after every routing change. The MCP `connectivity` tool
re-runs sch2mag, which *replaces* the layout it is asked about: right
for an sch2mag design, wrong for a ciccreator library, and it will
overwrite the .mag you were checking.

A tap-less leaf cell reports its supply rails split. That is the library
design, not a defect.

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

## Worked example

`LELO_TEMP_SKY130A/LELOTEMP_OTA.py` in lelo_temp_sky130a exercises all of
this: netlist driven grouping with renames, folded ten device groups into
mirrored five device halves, dummy fill, tap fallback for LVT devices,
and every spacing in the table above. `LELOTEMP_CMP.py` in the same
library is the reference for the routing phase.
