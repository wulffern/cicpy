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
    accessLayer=None,
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
- `accessLayer`: terminal access layer collected with `instance.getTerminalAccess(...)`; defaults to `verticalLayer`

Behavior:
- collects terminal access rectangles on `accessLayer`
- finds a free vertical trunk track on `verticalLayer`
- creates horizontal branches on `horizontalLayer`
- uses `1x2` for vertical access rectangles and `2x1` for horizontal access rectangles
- places a `1x2` trunk cut between branch and trunk

Example:

```python
layout.addOrthogonalConnectivityRoute("M2", "M3", r"^D$", "nolabel", 1, "", "", accessLayer="M1")
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

### Working options

- `onTopB`, `onTopT`, `onTopL`, `onTopR`
  Used mainly by `addRouteConnection(...)` to choose which rectangle becomes the start rectangle.
- `offsethigh`, `offsetlow`
  Offsets the start-side horizontal stub by one route width.
- `offsethighend`, `offsetlowend`
  Offsets the stop-side horizontal stub by one route width.
- `trackN`
  Moves the left/right trunk by `N * ROUTE.horizontalgrid`.
- `routeWidth=<rule>`
  Uses another width rule from the technology file instead of `width`.
- `startLayer=<layer>`, `stopLayer=<layer>`
  Forces the copied start/stop rectangles onto a specific layer before route generation.
- `trimstartleft`, `trimstartright`, `trimendleft`, `trimendright`
  Trims the source rectangles before building left/right routes.
- `leftdownleftup`, `leftupleftdown`
  Selects the specialized detour routes shown above.
- `strap`
  Uses strap routing instead of the normal left/right/straight logic.
- `vertical`
  Only meaningful together with `strap`; switches strap routing to vertical.
- `noSpace`
  Removes the default space between the source geometry and the left/right trunk.
- `novert`
  Disables the trunk segment in left/right routes.
- `fillhcut`
  Forces horizontal `2x1` cuts on horizontal access rectangles.
- `fillvcut`
  Forces vertical `1x2` cuts on vertical access rectangles.
- `antenna`
  Promotes tall vertical routes two layers up when legal.
- `nolabel`
  Suppresses route net-name text in the output.

### Classic cut options

- `nostartcut`, `noendcut`
- `startoffsetcuthigh`, `startoffsetcutlow`
- `endoffsetcuthigh`, `endoffsetcutlow`
- `<N>startcuts`, `<N>startvcuts`
- `<N>endcuts`, `<N>endvcuts`
- `<N>cuts`, `<N>vcuts`

Current constraint:
- all generated cuts are normalized to `1x2` or `2x1`
- `1x1` is not used

## Lower-level escape hatch

### `addDirectedRoute(...)`

`addDirectedRoute(...)` still exists for explicit path routing, but it is not the default API for these docs.
Use it when routing must be driven by a specific instance-path expression instead of a shared net in `nodeGraph`.
