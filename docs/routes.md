---
layout: default
title: Routing
nav_order: 3
---

# Routes

Preferred routing APIs in `cicpy`:
- `addConnectivityRoute(...)`
- `addOrthogonalConnectivityRoute(...)`

These are the APIs the examples below use. `addDirectedRoute(...)` still exists, but it is a lower-level escape hatch and is not the default path for normal layout generation.

The examples below are generated from:
- `tests/routes/route_examples.spi`
- `tests/routes/build_route_examples.py`

Flow used by the examples:
- parse a tiny SPICE file with one subckt per route demo
- build a `LayoutCell` from each subckt
- call `place()` so the instances create a real `nodeGraph`
- route by net name with `addConnectivityRoute(...)` or `addOrthogonalConnectivityRoute(...)`
- render the result with `SvgPrinter`

The transistor used in every example is the real `NCHDL` cell from the SVG regression data. Routes land on actual `G`, `S`, or `D` terminals.

## Preferred APIs

### Paths: a route as a story

The twelfth shape, and the one to reach for when the canned strings
below run out — or whenever the route should *say why it is where it
is*. A `Path` is a sequence of steps, each aimed at something **named
in the design**; there is deliberately no way to write a coordinate.

```python
p = layout.path("RST_A", "M2", start=[pin_a], stop=[pin_b])
p.movey(p.track("cband", 2))     # a channel lane
p.up("M4")                       # layer change (largest cut that fits)
p.movex(p.track("dband", 2))
p.movey(p.landing("y"))          # the stop rect's row
p.movex(p.landing("x"))          # ...and its column
p.end()                          # land on the stop rect
```

**Steps**: `start(at=)` / `end(at=)` (the ends are PORTS, used where
they are; `at="n|s|e|w"` picks an edge of the rect), `movex(anchor)` /
`movey(anchor)`, `up(layer=)` / `down(layer=)`, `trunk(at=)` (ride a
lane the length of the route's own pins), `comb` (one trunk, a stub
per pin), `merge` (bring every pin sideways onto one lane, no vias),
`taps` (come back DOWN onto every pin from the lane being ridden — the
other half of a flyover).

**Anchors**: `pin(inst, net, axis)`, `track(channel, index)`,
`landing(axis)`, `tab_lane()`, `right_of_pins()`, `left_of_pins()` —
each may take `± n*PITCH` or `± SPACE`, units read from the
technology. All resolve at draw time, so a story survives a resize
and another technology.

**Options** are the same string the canned shapes take — cut counts
(`1cuts,2vcuts`), and `noendcut` when the story lands where the child
has already brought the net up (a second stack on one pin is a
partial overlap magic tolerates and klayout does not).

The declarative form lives on the sidecar classes as `paths` entries
— including the collected-pin form for column rails, where no
start/stop is named and the rail grows over any device added to the
column. The loop that produces these entries from a search — emit,
import, verify — is the
[field guide](/cicpy/agent_layout)'s own section.

`CICPY_TRACE=<net>` prints where every step of that net resolved.


### `addConnectivityRoute(...)`

```python
layout.addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances, includeInstances)
```

Arguments:
- `layer`: routing layer used by the route object
- `regex`: regular expression matched against `nodeGraphList` net names
- `routeType`: one of the route strings documented below
- `options`: comma-separated route options
- `cuts`: accepted by the API but currently not consumed directly by `Route`; cut count is instead parsed from `options`
- `excludeInstances`: regex used to drop instance names from the candidate rectangle set
- `includeInstances`: regex used to keep only a subset of instance names

Example:

```python
layout.addConnectivityRoute("M3", r"^G$", "-", "nolabel", 1, "", "")
```

### `addOrthogonalConnectivityRoute(...)`

```python
layout.addOrthogonalConnectivityRoute(
    verticalLayer,
    horizontalLayer,
    regex,
    options,
    cuts,
    excludeInstances,
    includeInstances,
)
```

Arguments:
- `verticalLayer`: layer used for the trunk
- `horizontalLayer`: layer used for branches
- `regex`: net regex matched against `nodeGraphList`
- `options`: currently accepted for API symmetry; route-label suppression uses `nolabel`
- `cuts`: currently stored but not used to size the cuts; the implementation uses `1x2` or `2x1`
- `excludeInstances`: regex for dropping instances
- `includeInstances`: regex for limiting candidate instances

Behavior:
- collects port rectangles on whatever layer the device exposes (group boundary ports first, then instance ports); the route engine adds the cuts to bridge to `verticalLayer` / `horizontalLayer`
- finds a free vertical trunk track on `verticalLayer`
- creates horizontal branches on `horizontalLayer`
- uses `1x2` for vertical access rectangles and `2x1` for horizontal access rectangles
- places a `1x2` trunk cut between branch and trunk

Example:

```python
layout.addOrthogonalConnectivityRoute("M2", "M3", r"^D$", "nolabel", 1, "", "")
```

## Route types

### Straight `-`

Connects one instance terminal to one other instance terminal with horizontal metal on one layer.

```bash
make test PYTHON=/opt/eda/python3/bin//python3
```

![](/cicpy/assets/ROUTE_STRAIGHT.svg)


### Straight with layer transition

A straight route can also add start/end cuts when the source rectangles are on another layer.
This example routes on `M3` from `NCHDL:D` and uses `fillvcut` plus start/end cut offsets.

![](/cicpy/assets/ROUTE_STRAIGHT_WITH_CUTS.svg)


### Straight with horizontal fill cuts

This example uses `fillhcut` on `NCHDL:G`.

![](/cicpy/assets/ROUTE_STRAIGHT_WITH_FILLHCUT.svg)


### Left `-|--`

Routes one-to-many on shared net `D` from two left-column instances to one right-column instance.

![](/cicpy/assets/ROUTE_LEFT.svg)


### Right `--|-`

Routes one-to-many on shared net `S` from one left-column instance to two right-column instances.

![](/cicpy/assets/ROUTE_RIGHT.svg)


### Vertical `||`

Creates a straight vertical connection between stacked `NCHDL:D` terminals.

![](/cicpy/assets/ROUTE_VERTICAL.svg)


### Vertical with antenna

With `antenna`, the vertical trunk is promoted two routing layers up when there is enough height, with `1x2` cuts at the two ends.
If there is not enough height, it falls back to the normal vertical trunk.

![](/cicpy/assets/ROUTE_VERTICAL_ANTENNA.svg)


### U left `|-`

Builds a vertical trunk to the left of stacked `NCHDL:D` terminals and reconnects both ends back into it.

![](/cicpy/assets/ROUTE_U_LEFT.svg)


### U right `-|`

Builds a vertical trunk to the right of stacked `NCHDL:D` terminals and reconnects both ends back into it.

![](/cicpy/assets/ROUTE_U_RIGHT.svg)


### U top `--|`

Builds a horizontal bar above two `NCHDL:G` terminals and drops vertical stubs down to them.

![](/cicpy/assets/ROUTE_U_TOP.svg)


### U bottom `|--`

Builds a horizontal bar below two `NCHDL:G` terminals and rises vertical stubs up to them.

![](/cicpy/assets/ROUTE_U_BOTTOM.svg)


### Left-down-left-up

Enabled with route type `-|--` plus option `leftdownleftup`.
This is a specialized two-level detour shape.

![](/cicpy/assets/ROUTE_LEFT_DOWN_LEFT_UP.svg)


### Left-up-left-down

Enabled with route type `-|--` plus option `leftupleftdown`.
This is the mirrored specialized two-level detour.

![](/cicpy/assets/ROUTE_LULD.svg)


### Strap

Enabled with option `strap`.
- default: horizontal one-to-many straps from one anchor terminal to several peers
- add `vertical` to strap vertically instead

Horizontal strap:

![](/cicpy/assets/ROUTE_STRAP_HORIZONTAL.svg)


Vertical strap:

![](/cicpy/assets/ROUTE_STRAP_VERTICAL.svg)


### Orthogonal connectivity route

This is the preferred two-layer routing API for a vertical trunk plus horizontal branches.
The demo uses shared net `D` and collects `M1` device access before routing on `M2` and `M3`.

![](/cicpy/assets/ROUTE_ORTHOGONAL.svg)


## Options

`options` is a comma-separated string. Current `Route` parsing in `cicpy` supports these names.

### Naming, and one trap in it

Two option families have nearly the same names and nothing to do with
each other. Read this before using either.

| option | what it names | what it does |
|---|---|---|
| `startLayer=<L>`, `stopLayer=<L>` | the route's two ENDS | relabels the copied start/stop rectangles onto layer `L` before routing |
| `startStopLayer<L>`, `endStopLayer<L>` | where the VIA STACK at that end lands | truncates the stack, so it stops at `L` instead of driving down to the pin's own layer |

"stop" means the far end of the route in the first family and the end
of the via stack in the second. Only the second is about vias.

### Working options

- `onTopB`, `onTopT`, `onTopL`, `onTopR`
  Chooses which rectangle sorts to the front and becomes the start
  rectangle. `onTopTop`, `onTopBottom`, `onTopLeft`, `onTopRight` are a
  different setting -- they set the ANCHOR MODE of an orthogonal route.
- `left`, `right`, `center` / `balanced`
  Which way an orthogonal route counts its track offsets.
- `offsethigh`, `offsetlow`
  Offsets the start-side horizontal stub by one route width.
- `offsethighend`, `offsetlowend`
  Offsets the stop-side horizontal stub by one route width.
- `verticaltrackN`
  Moves the vertical trunk by `N` tracks. Signed values are supported, for
  example `verticaltrack-1`, `verticaltrack-8`, and `verticaltrack+3`.
  `trackN` is kept as a backward-compatible alias.
- `horizontaltrackN`
  Moves orthogonal route branches to an alternate horizontal track. Signed
  values are supported, for example `horizontaltrack-2`. `branchtrackN` is kept
  as a backward-compatible alias.
- `trunktab`, `trunkright`, `trunkleft`
  WHERE THE TRUNK GOES, named from the pins instead of measured. `trunktab`
  is the centre of the rightmost narrow pin, `trunkright` the right edge of
  the pins' common overlap, `trunkleft` its left edge. These are what a
  design should say: each survives a resize and a change of technology.
  The router emits these, never a coordinate.
- `routeWidth=<rule>`
  Uses another width rule from the technology file instead of `width`.
- `startLayer=<layer>`, `stopLayer=<layer>`
  Forces the copied start/stop rectangles onto a specific layer before route
  generation. Not about vias -- see the table above.
- `trimstartleft`, `trimstartright`, `trimendleft`, `trimendright`
  Trims the source rectangles before building left/right routes.
- `leftdownleftup`, `leftupleftdown`
  Selects the specialized detour routes shown above.
- `straight`
  Only meaningful on `-|-`, which carries no alignment of its own.
- `strap`
  Uses strap routing instead of the normal left/right/straight logic.
- `vertical`
  Only meaningful together with `strap`; switches strap routing to vertical.
- `noSpace`
  Removes the default space between the source geometry and the left/right trunk.
- `novert`
  Disables the trunk segment in left/right routes.
- `antenna`
  Promotes tall vertical routes two layers up when legal.
- `nolabel`
  Suppresses route net-name text in the output.
- `avoidblocks`, `avoidboundaries` / `blockboundaries`,
  `avoidkeepouts` / `blockkeepouts`, `keepout=<name>`
  Treats blocks, cell boundaries or named keepouts as obstacles.

### Cut options

- `<N>cuts`, `<N>vcuts` -- the array, horizontally and vertically.
- `<N>startcuts`, `<N>startvcuts`, `<N>endcuts`, `<N>endvcuts` -- one end only.
- `nostartcut`, `noendcut` -- no cut at that end at all.
- `startoffsetcuthigh` / `startoffsetcutlow`,
  `endoffsetcuthigh` / `endoffsetcutlow` -- shifts that end's cut by half its
  height, and the rect with it.
- `fillhcut`, `fillvcut`
  Forces `2x1` on a horizontal access rect, `1x2` on a vertical one. These
  REINFORCE the aspect heuristic; they cannot overrule it.
- `cutv`, `cuth`, and the per-end `startcutv` / `startcuth` /
  `endcutv` / `endcuth`
  Forces the array's DIRECTION regardless of the rect's aspect. Use when the
  heuristic itself is wrong -- on a wide pin it makes a pad several times the
  width of the wire, and the pad is what collides with the neighbour.
- `cutalignright`, `cutaligncenter`
  Where the landing pad sits on a pin wider than the cut. Left is the
  default. Centre is right when the trunk meets the pin in its middle and
  wrong when a neighbour runs there.
- `startStopLayer<L>`, `endStopLayer<L>` (an `=` is optional)
  **Meet the pin on the metal it has already been brought up to.** A pin
  normally arrives with its own via under it -- a li pin has an mcon, a MiM
  plate has its stack, and a SUBCELL's own route may have taken its port one
  layer up. A route that drives all the way down to the pin's layer then
  lands a second via on the first: two contacts of one type, partially
  overlapping, which magic reports as

      This layer can't abut or partially overlap between subcells

  Naming the layer the pin is already carried to leaves one via and one set
  of pads. `promoteInstancePort(..., stopLayer="M2")` is the same option on
  a riser stack, and `Cut.getCutsForRects(..., stopLayer=)` is the same word
  one level down.

Current constraint:
- all generated cuts are normalized to `1x2` or `2x1`
- `1x1` is not used

### Options a design should NOT write

- `trunkx=<n>`, `bandy=<n>`
  Absolute coordinates. They exist only as the resolved form of
  `vchannel`/`hchannel`, which is what a pycell writes. A coordinate
  survives neither a resize nor another technology -- use a trunk anchor
  above, or a channel and a track index.

## Lower-level escape hatch

### `addDirectedRoute(...)`

`addDirectedRoute(...)` still exists for explicit path routing, but it is not the default API for these docs.
Use it when routing must be driven by a specific instance-path expression instead of a shared net in `nodeGraph`.
