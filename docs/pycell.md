# Custom Pycell API

When `cicpy sch2mag` or `cicpy spi2mag` processes a cell, it looks for a Python file named `<CELL>.py` in the cell's library directory. If found, the file is imported and its hook functions are called at defined points in the layout pipeline.

If the file does not exist, `spi2mag`/`sch2mag` creates a default commented template with the available hooks. Existing files are never overwritten.

This page documents the hook protocol and every API that is safe to call from a pycell.

## File Location and Loading

```
design/<LIB>/<CELL>.py
```

The file is imported dynamically. It receives the `LayoutCell` object (`layout`) as the first argument to every hook function.

The file may also expose a top-level `data` dict (see [Data dict hooks](#data-dict-hooks)).

## Hook Execution Order

```
beforePlace(layout)
  → default place()
afterPlace(layout)
  → internal dummy-route materialization
beforeRoute(layout)
  → default route()
afterRoute(layout)
beforePaint(layout)
  → addAllPorts() and paint
afterPaint(layout)
```

Not every hook needs to be defined. Only define the ones your cell requires.

## Hook Functions

### `beforePlace(layout)`

Set coarse global policy before placement runs.

```python
def beforePlace(layout):
    layout.noPowerRoute = True          # disable automatic M4 power sheet
    layout.place_xspace = [0]           # horizontal gap between groups (tech units)
    layout.place_yspace = [0]           # vertical gap between groups (tech units)
    layout.place_groupbreak = [5]       # wrap to new column every N groups
```

### `afterPlace(layout)`

Reshape the physical organization after the default placement. This is where the floorplan is built.

```python
def afterPlace(layout):
    nmos = layout.makeCellGroup("nmos")
    stack = nmos.addStack("bias", layout.getSortedInstancesByInstanceName("xbias"))
    stack.addTaps()
    nmos.routeDummyDevices()

    pmos = layout.makeCellGroup("pmos")
    pmos.abutRight(nmos, space=2 * layout.um)
    pmos.updateBoundingRect()
    nmos.updateBoundingRect()
```

### `beforeRoute(layout)`

Express all routing intent. Called after placement and dummy-route setup are complete.

```python
def beforeRoute(layout):
    layout.addRouteRing("M1", "VDD", "t", widthmult=3, spacemult=2)
    layout.addRouteRing("M1", "VSS", "b", widthmult=3, spacemult=2)
    layout.addPowerConnection("VDD", "", "top")
    layout.addPowerConnection("VSS", "", "bottom")
    layout.addConnectivityRoute("M2", "^IBP$", "||", "", 1, "NCH", "")
    layout.addOrthogonalConnectivityRoute("M2", "M3", "^VOUT$", "track0", 1, "", "")
```

### `afterRoute(layout)`

Post-route adjustments. Use this only for changes that depend on routing geometry already existing.

### `beforePaint(layout)`

Late-stage work after routing, before the final paint/port phase.

### `afterPaint(layout)`

Final adjustments before ports are added. Commonly used to normalize the origin:

```python
def afterPaint(layout):
    layout.resetOrigin(1)
```

---

## Data Dict Hooks

Instead of (or in addition to) Python functions, a pycell can define a top-level `data` dict. This lets simple method calls be expressed as configuration rather than code.

```python
data = {
    "afterPaint": [
        {"resetOrigins": [[1]]},
    ]
}
```

Each key matches a hook name. The value is a list of `{methodName: [args]}` dicts. The method is called on the `LayoutCell` object with the given arguments. Plural method names (ending in `s`) are expanded to call the singular form once per item in the list.

---

## LayoutCell API

The `layout` object passed to every hook is a `LayoutCell`. The following methods are available from pycell files.

### Placement control properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `layout.um` | `int` | `10000` | Scale factor: 1 µm in tech units |
| `layout.noPowerRoute` | `bool` | `False` | Disable automatic M4 power sheet generation |
| `layout.place_xspace` | `list[int]` | `[space]` | Horizontal gap(s) between groups in tech units |
| `layout.place_yspace` | `list[int]` | `[space]` | Vertical gap(s) between groups in tech units |
| `layout.place_groupbreak` | `list[int]` | `[100]` | Wrap to new column after every N groups |

### Placement methods

#### `makeCellGroup(name) → CellGroup`

Create a new named `CellGroup`. Instances must be added to the group via `addStack` or `addInstances`.

```python
nmos = layout.makeCellGroup("nmos")
```

#### `getSortedInstancesByInstanceName(regex) → list`

Return instances whose instance names match `regex`, sorted naturally by name.

```python
insts = layout.getSortedInstancesByInstanceName("xbias")
```

#### `getSortedInstancesByGroupName(groupName, excludeInstances="") → list`

Return instances whose schematic-derived `groupName` exactly matches `groupName`,
sorted in natural instance-name order. The group name is normally the non-numeric
prefix of the schematic instance name, so `xn_bias1`, `xn_bias2<0>`, and
`xn_bias10` all belong to `xn_bias`.

Use this when stack membership should be controlled by schematic naming instead
of by a broad regular expression.

```python
insts = layout.getSortedInstancesByGroupName("xn_bias")
```

#### `getInstancesByName(regex) → list`

Return instances whose cell names match `regex`.

#### `getInstancesByCellname(regex) → list`

Return instances whose subcell name matches `regex`.

#### `getInstanceFromInstanceName(instanceName) → Instance | None`

Return the single instance with the given exact instance name.

```python
inst = layout.getInstanceFromInstanceName("xbias<0>")
```

#### `addPhysicalInstance(cellName, instanceName, x, y) → Instance`

Place a cell by name at an explicit coordinate without a netlist entry.

#### `placeHorizontal(val)`

When `val` is truthy, stack instances horizontally within groups instead of vertically.

#### `resetOrigin(val)`

When `val` is truthy, translate the entire layout so its lower-left corner is at (0, 0).

#### `setYoffsetHalf(val)`

When `val` is truthy, use half-height Y offsets during placement.

#### `alternateGroupFlag()`

Enable alternating-group placement mode.

#### `noPowerRouteFlag()`

Disable power routing (same effect as setting `layout.noPowerRoute = True`).

---

### Routing methods

#### `addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances, includeInstances)`

Connect all instances whose net name matches `regex` on the given `layer`.

| Parameter | Description |
|-----------|-------------|
| `layer` | Metal layer, e.g. `"M2"` |
| `regex` | Net name regex, e.g. `"^IBP$"` |
| `routeType` | Shape of the route (see table below) |
| `options` | Comma-separated option string (see below) |
| `cuts` | Number of via cuts per connection |
| `excludeInstances` | Regex; skip instances whose name matches |
| `includeInstances` | Regex; only include instances whose name matches |

**Route types:**

| `routeType` | Shape |
|-------------|-------|
| `"-"` | Horizontal bar |
| `"\|\|"` | Vertical bar |
| `"-\|--"` | L-shape, trunk on left |
| `"--\|-"` | L-shape, trunk on right |
| `"-\|--\|-"` | U-shape |

**Common options:**

| Option | Effect |
|--------|--------|
| `onTopB` | Route to top edge of bounding box |
| `onTopT` | Route to bottom edge of bounding box |
| `onTopL` | Route to left edge |
| `onTopR` | Route to right edge |
| `fillvcut` | Fill vertical cut columns |
| `fillhcut` | Fill horizontal cut rows |
| `left` | Track direction: left |
| `right` | Track direction: right |
| `center` | Track direction: centered |
| `verticaltrackN` | Use vertical trunk track N (`trackN` alias supported) |
| `horizontaltrackN` | Use horizontal branch track N (`branchtrackN` alias supported) |

#### `addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, includeInstances, accessLayer=None)`

Route a net using explicit vertical and horizontal layers. Suitable for multi-layer routes where vertical and horizontal segments should stay on different metals.

```python
layout.addOrthogonalConnectivityRoute("M2", "M3", "^VOUT$", "track0", 1, "", "")
```

`accessLayer` defaults to `verticalLayer`. Set it to select which layer is used to reach the device terminal.

#### `addDirectedRoute(layer, net, route, options="")`

Route between two sets of rectangles found by name patterns.

```python
layout.addDirectedRoute("M2", "VOUT", "xbias-|--xdiff", "")
```

`route` format: `startRegex + routeSymbols + stopRegex` where route symbols are the same as `routeType` above.

#### `addOrthogonalRouteFromRects(net, verticalLayer, horizontalLayer, rects, options="", cuts=1)`

Route a net using an explicit list of `Rect` objects as access points. Use when the connectivity graph does not have the right rects.

---

### Ring and rail methods

#### `addRouteRing(layer, name, location="rtbl", widthmult=1, spacemult=2, useGridForSpace=True)`

Add a routing ring for net `name` on `layer`. The ring is placed at `spacemult × grid` outside the cell boundary.

`location` is a string of sides: `r` (right), `t` (top), `b` (bottom), `l` (left). Use `"t"` for a top-only rail, `"rtbl"` for a full ring.

After calling this, the ring sides are accessible as:
- `layout.named_rects["rail_<name>"]` — full ring
- `layout.named_rects["rail_t_<name>"]`, `rail_b_`, `rail_l_`, `rail_r_` — individual sides

#### `addPowerRing(layer, name, location="rtbl", widthmult=1, spacemult=10)`

Add a power ring (wider than a routing ring; sized relative to via stack height). After calling this, sides are accessible as:
- `layout.named_rects["power_<name>"]`
- `layout.named_rects["RAIL_TOP_<name>"]`, `RAIL_BOTTOM_`, `RAIL_LEFT_`, `RAIL_RIGHT_`

#### `addPowerConnection(name, includeInstances, location, excludeInstances="")`

Connect all instances of net `name` to the power ring for `name` at the given side (`"top"`, `"bottom"`, `"left"`, `"right"`).

```python
layout.addPowerConnection("VDD", "", "top")
layout.addPowerConnection("VSS", "^xbias", "bottom")   # only xbias instances
layout.addPowerConnection("VDD", "", "top", "^xfill_")  # skip explicit fillers
```

#### `addRouteConnection(path, includeInstances, layer, location, options, routeTypeOverride="", excludeInstances="")`

Connect instances of nets matching `path` to their routing rail at the given side.

```python
layout.addRouteConnection("^VBP2$", "", "M4", "top", "")
layout.addRouteConnection("^VBP2$", "", "M4", "top", "", excludeInstances="^xfill_")
```

#### `addRouteGroup(net) → RouteGroup`

Return a chainable route builder for one logical net. A route group emits normal
routes internally, but lets a pycell describe a trunk-and-exit route as one
logical operation.

```python
layout.addRouteGroup("VBP2").trunk("M3", side="top", includeInstances="^xp").exit("right")
```

`trunk(...)` creates a horizontal trunk plus local spurs to matched anchors.
`exit(...)` exposes the same net on a cell edge using `addPortOnEdge(...)`.

---

### Geometry methods

#### `addRectangle(layer, x1, y1, width, height, angle="")`

Add a raw rectangle. Coordinates are in tech units. `angle` can be `""`, `"R90"`, `"R180"`, `"R270"`.

#### `addPortRectangle(layer, x1, y1, width, height, angle, portname)`

Add a rectangle and register it as a named port.

#### `addVerticalRect(layer, path, cuts=0)`

Extend rectangles matching `path` on `layer` to the full cell height.

#### `addHorizontalRect(layer, path, xsize=1, ysize=1)`

Add a horizontal rectangle offset from rectangles matching `path`.

#### `addRouteHorizontalRect(layer, rectpath, x, name="")`

Add a horizontal rectangle of width `x × horizontalgrid` starting from rectangles matching `rectpath`.

#### `addPortOnEdge(layer, node, location, routeType, options)`

Move the port rectangle for net `node` to the cell edge (`"top"`, `"bottom"`, `"left"`, `"right"`).

```python
layout.addPortOnEdge("M2", "VOUT", "left", "||", "")
```

---

### Query methods

#### `findRectanglesByNode(node, filterChild=None, matchInstance=None) → list[Rect]`

Return all rectangles carrying net `node` from child instances. `filterChild` excludes ports whose name matches the regex. `matchInstance` restricts to instances whose name matches.

#### `getOccupiedRectangles(layer, excludeInstances="", ignoreNet="") → list[Rect]`

Return all physical rectangles on `layer` from placed instances.

#### `getNodeGraphs(regex) → list[Graph]`

Return connectivity graphs for all nets matching `regex`.

---

## CellGroup API

`CellGroup` objects are created with `layout.makeCellGroup(name)`. They represent a physical region containing one or more stacks.

### Building structure

#### `addStack(name, instances) → Stack`

Add a named stack of instances to the group. Returns the `Stack`.

```python
stack = nmos.addStack("bias_ref", layout.getSortedInstancesByInstanceName("xbias"))
```

#### `addStackByGroup(groupName, name=None, fillGroup=None) → Stack`

Create a stack from all instances whose `groupName` exactly matches `groupName`.
Instances are placed in natural name order. If `fillGroup` is provided, those
instances are appended after the real devices, so explicit schematic fillers stay
at the top of the stack.

```python
n_vbn = nmos.addStackByGroup("xn_vbn")
n_vp = nmos.addStackByGroup("xn_vp", fillGroup="xfill_xn_vp")
```

#### `addTaps()` *(on Stack)*

Add `CTAPBOT` and `CTAPTOP` dummy tap devices around the stack.

#### `routeDummyDevices()`

Route internal dummy device connections on M1. Must be called after `addTaps()`. **Do not add signal routes on M1 after this call.**

#### `fillDummyTransistors(direction="top")` *(on CellGroup)*

Fill remaining space in the group with dummy transistors. `direction` is `"top"` or `"bottom"`.

### Positioning

#### `abutRight(other, space=0)`

Place `other` to the right of `self` with `space` gap in tech units.

#### `abutLeft(other, space=0)`

Place `other` to the left of `self`.

#### `abutTop(other, space=0)`

Place `other` above `self`.

#### `abutBottom(other, space=0)`

Place `other` below `self`.

#### `updateBoundingRect()`

Recalculate the group's bounding box after structural changes.

### Routing (on CellGroup or Stack)

Groups and stacks expose a scoped version of the routing APIs. These route only within the group's instance set:

```python
nmos.addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances)
nmos.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, accessLayer)
```

---

## Complete Example

```python
# design/MYLIB/MYCELL.py

data = {
    "afterPaint": [
        {"resetOrigins": [[1]]},
    ]
}

def beforePlace(layout):
    layout.noPowerRoute = True
    layout.place_xspace = [0]
    layout.place_yspace = [0]
    layout.place_groupbreak = [4]

def afterPlace(layout):
    branch_gap = 2 * layout.um

    nmos = layout.makeCellGroup("nmos")
    bias  = nmos.addStack("bias",  layout.getSortedInstancesByInstanceName("xbias"))
    diff  = nmos.addStack("diff",  layout.getSortedInstancesByInstanceName("xdiff"))

    pmos = layout.makeCellGroup("pmos")
    load  = pmos.addStack("load",  layout.getSortedInstancesByInstanceName("xload"))

    pmos.abutRight(nmos, space=branch_gap)

    bias.addTaps()
    diff.addTaps()
    load.addTaps()

    nmos.updateBoundingRect()
    pmos.updateBoundingRect()
    nmos.routeDummyDevices()
    pmos.routeDummyDevices()

    # stash groups for use in beforeRoute
    layout._scopes = {"nmos": nmos, "pmos": pmos, "bias": bias, "diff": diff}

def beforeRoute(layout):
    scopes = layout._scopes
    nmos = scopes["nmos"]
    pmos = scopes["pmos"]

    layout.addRouteRing("M1", "VDD", "t", widthmult=3, spacemult=2)
    layout.addRouteRing("M1", "VSS", "b", widthmult=3, spacemult=2)
    layout.addPowerConnection("VDD", "", "top")
    layout.addPowerConnection("VSS", "", "bottom")

    # Bias net: vertical M2 trunk connecting all xbias instances
    scopes["bias"].addConnectivityRoute("M2", "^IBP$", "||", "", 1, "")

    # Output: orthogonal route using M2 vertical / M3 horizontal
    layout.addOrthogonalConnectivityRoute("M2", "M3", "^VOUT$", "onTopLeft,track4", 1, "", "")
```
