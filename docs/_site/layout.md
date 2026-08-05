# Layout Flow

This page explains how `cicpy sch2mag` actually builds layout, and where placement and routing intent is supposed to live.

## Entry Points

There are two main layout-generation entry points:

```bash
cicpy sch2mag <LIB> <CELL>
cicpy spi2mag <SPICE> <LIB> <CELL>
```

- `sch2mag` starts from a schematic-driven project and first generates a SPICE netlist.
- `spi2mag` starts from an existing SPICE subcircuit.

Both end up building a `LayoutCell`, placing instances, running Python hooks, routing, and writing `.mag` and `.cic` output.

## High-Level Flow

For `sch2mag`, the flow is:

1. netlist the schematic to SPICE
2. load technology rules from `tech/cic/<tech>.tech`
3. scan the design library path for primitive Magic cells
4. read the target SPICE subckt into a `LayoutCell`
5. apply default placement from instance names and grouping
6. import `<CELL>.py` if it exists
7. run layout hooks from that Python file
8. finish routing and paint
9. write `<CELL>.mag`
10. write `<CELL>.cic`
11. optionally run route-short and full connectivity checks

The key point is that the flow is schematic-driven, but not schematic-only. The schematic provides devices, nets, and grouping names. The Python file provides physical intent.

## Inputs

A practical `sch2mag` run uses:

- a SPICE netlist for the target cell
- primitive layout libraries under the design tree
- a technology rules file
- an optional custom Python cell file named `<CELL>.py`

Typical project structure:

- `design/<LIB>/<CELL>.sch`
- `design/<LIB>/<CELL>.py`
- `design/<primitive_lib>/...`
- `tech/cic/<tech>.tech`

## Default Placement

Before any custom Python runs, `cicpy` derives a first placement from the instance list.

The default model relies heavily on naming:

- the non-numeric instance prefix becomes the placement group
- similarly named bus instances naturally stack together
- group order and stack composition are therefore strongly affected by schematic naming

That is why good schematic instance naming matters. If placement is wrong, the first fix is often to rename instances so the automatic grouping matches the intended physical columns.

## Custom Python Hooks

If `design/<LIB>/<CELL>.py` exists, `sch2mag` imports it and uses its hook functions.

The supported hook functions are:

- `beforePlace(layout)`
- `afterPlace(layout)`
- `beforeRoute(layout)`
- `afterRoute(layout)`
- `beforePaint(layout)`
- `afterPaint(layout)`

Not every cell uses every hook.

The execution order is:

1. `beforePlace(layout)`
2. default `place()`
3. `afterPlace(layout)`
4. internal dummy-route materialization and tile-map setup
5. `beforeRoute(layout)`
6. default `route()`
7. `afterRoute(layout)`
8. `beforePaint(layout)`
9. late paint/post-processing stage
10. `afterPaint(layout)`
11. `addAllPorts()`

### `beforePlace(layout)`

Use this for coarse global controls such as:

- disabling default power paint with `layout.noPowerRoute = True`
- tuning group spacing with `layout.place_xspace`, `layout.place_yspace`
- changing group wrap behavior with `layout.place_groupbreak`

This hook should set broad layout policy, not hand-place individual routes.

### `afterPlace(layout)`

Use this to reshape the physical organization after the default placement exists.

Typical work here:

- create `CellGroup`s
- create functional stacks with `group.addStack(...)`
- abut groups with `abutTop`, `abutBottom`, `abutLeft`, `abutRight`
- add taps with `stack.addTaps()`
- add dummy devices or route dummy devices
- update bounding boxes after structural edits

This is where analog floorplan intent usually belongs.

### `beforeRoute(layout)`

Use this for explicit routing and supply hookup.

Typical calls are:

```python
layout.addRouteRing(...)
layout.addPowerConnection(...)
layout.addRouteConnection(...)
layout.addConnectivityRoute(...)
layout.addOrthogonalConnectivityRoute(...)
```

This hook should express routing intent using the routing APIs, not by stamping arbitrary geometry unless there is no API for the job.

### `afterRoute(layout)`

Use this for changes that depend on the normal routing pass already being finished.

Typical uses:

- inspect or adjust route results
- add small post-route geometry
- add cleanup that should not affect route discovery itself

If something can be expressed directly through the normal routing APIs, prefer `beforeRoute(...)`.

### `beforePaint(layout)`

Use this for late-stage work after routing but before the final paint/post-processing phase completes.

Typical uses:

- prepare geometry for late finishing
- do final state adjustments after route creation
- stage cleanup that should happen after the route graph is already settled

This is a less common hook than `beforePlace`, `afterPlace`, and `beforeRoute`.

### `afterPaint(layout)`

Use this for the final structural adjustments before ports are added.

Typical uses:

- normalize origins
- final cleanup
- last-step geometry adjustments that should happen after placement and routing are complete

## Placement APIs

The most common physical-organization APIs are:

```python
group = layout.makeCellGroup("name")
stack = group.addStack("stack_name", instances)
stack.addTaps()
group.abutRight(other, space=...)
group.abutTop(other, space=...)
group.fillDummyTransistors(...)
```

These APIs let a cell be described in terms of physical branches and matched stacks, rather than individual coordinates.

## Routing APIs

The two normal routing APIs are:

```python
layout.addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances, includeInstances)
layout.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, includeInstances, accessLayer=None)
```

Use them as the default choice.

- `addConnectivityRoute(...)` is the standard net-driven router for straight, L, U, and vertical routes.
- `addOrthogonalConnectivityRoute(...)` is better when the flow must follow explicit vertical/horizontal layer policy.

In analog sky130-style flows, that often means:

- M2 vertical trunks
- M3 horizontal branches
- M4 vertical trunks for higher-level routes

## Terminal Access And Cuts

A recurring rule in `cicpy` is that terminal access should come from the primitive device layout, not from guessed landing bars.

Preferred pattern:

- use legal device access geometry already exposed by the primitive cell
- route into that access
- let the router place cuts

Current cut policy in this work:

- prefer only `1x2` or `2x1` cuts
- flatten cut geometry for Magic output when that is more robust than cut-cell references

## Outputs

The main generated files are:

- `<CELL>.mag`: Magic layout
- `<CELL>.cic`: JSON layout artifact

Important detail:

- the top-level `.cic` produced by `sch2mag` usually contains the target cell and generated cut cells
- referenced primitive library cells are typically not embedded in that same file

So for commands such as `cicpy svg`, include dependent library `.cic` files explicitly:

```bash
cicpy svg top.cic tech/cic/sky130A.tech TOP \
  --I analog_lib.cic \
  --I digital_lib.cic
```

That `--I` mechanism exists specifically so top-level generated cells can be rendered or inspected together with their referenced library cells.

## Debug Flow

Fast iteration:

```bash
cicpy sch2mag <LIB> <CELL>
```

Deeper connectivity check:

```bash
cicpy sch2mag --check-connectivity <LIB> <CELL>
```

Use the fast route-short report first. Use `--check-connectivity` when the question is opens or split nets rather than obvious shorts.

## Where Changes Should Go

The usual fix order is:

1. fix schematic instance naming if grouping is wrong
2. fix stack/group structure in `afterPlace(...)`
3. fix routing intent in `beforeRoute(...)`
4. only then add narrow custom geometry if the APIs still cannot express the requirement

That keeps the layout generator understandable and avoids burying physical intent in ad hoc geometry.

## Concrete Example

`LELOTEMP_CMP` is a good example of this flow in practice:

- `beforePlace(...)` disables default power routing and tightens placement spacing
- `afterPlace(...)` builds NMOS and PMOS groups, creates functional stacks, abuts them, and adds taps
- `beforeRoute(...)` adds power rings, supply hookups, and connectivity-driven signal routes
- `sch2mag --check-connectivity` is then used when route geometry looks correct but opens or splits still need to be checked
