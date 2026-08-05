# gui plan

Status: **Phases 1, 2, 2.5, 3, 4a–4d, and 4-ext all shipped.** The viewer
is a working planning surface: layout + schematic panes, cross-probing,
hierarchy nav, planning groups, connectivity check with flight lines,
route authoring, schematic rename, a nets panel with lasso select, and
layout hierarchy levels. Pycells consume the YAML via
`cicpy.groups.apply(layout)`. Remaining work is a short tail of polish
items — see [What's next](#whats-next).

See [`gui`](/cicpy/gui) for usage.

## Goal

Replace the C++ `cic-gui` (in `ciccreator/cic-gui/`) with a Python/PySide6
viewer hosted in `cicpy`. Add a schematic pane that renders XSchem
`.sch` files alongside the `.cic` layout, with cross-probing and
group-aware highlighting. Drive layout placement and routing decisions
from a sidecar `<Cell>.groups.yaml` authored in the GUI, consumed by the
placer via `cicpy.groups.apply()`.

The GUI is a **viewer + planning surface**, not a schematic editor.
XSchem remains the schematic editor (with the one exception of group
renames — see Phase 4-ext). ciccreator/cicpy remain the layout
generators; the GUI re-runs `spi2mag` after edits.

## Architecture

### Module layout (as shipped)

```
src/cicpy/gui/
  app.py                 QApplication bootstrap; CLI entry
  mainwindow.py          QMainWindow; splitter, file watcher, rerun, rename
  layout_scene.py        Walks Design → QGraphicsItems; member filter
  layout_view.py         QGraphicsView, Y-flip, wheel/rubber-band/F-fit
  schem_scene.py         Walks Schematic + recursive symbol render
  schem_view.py          QGraphicsView; lasso, shift-click multi-select
  sym_loader.py          Symbol path resolution + cache
  style.py               Layer rules → QPen/QBrush
  groups_panel.py        Planning groups list, edit/rename, ports & placement
  connectivity_panel.py  Run connectivity check; shorts/opens; flight lines
  nets_panel.py          Lists lab= nets; filter by active group / substring

src/cicpy/groups.py      Group / GroupSet dataclasses, YAML I/O, resolver,
                         apply() — emits addStack / addPortOnEdge /
                         addRouteConnection / addOrthogonalConnectivityRoute
                         from the resolved group set.
```

CLI: `cicpy gui FILE.cic [--tech tech.json] [--sch FILE.sch]`. Tech
auto-discovers from `<ipdir>/tech/cic/*.tech`; dependency libraries from
the IP `config.yaml`. `--no-auto-libs` disables.

PySide6 lives behind a `[gui]` extra so non-GUI users skip Qt.

### Grouping data model

`Group(name, kind, members, members_regex, members_nets, placement,
ports, routes, …)` in `src/cicpy/groups.py`. Persisted as a sidecar
`<CellName>.groups.yaml` next to the pycell `<CellName>.py`. Both GUI
(highlight, filter) and placer (`apply()`) call the same resolver.

**Member resolution unions three sources:** explicit `members` list,
`members_regex`, and `members_nets`. The pycell calls
`cicpy.groups.apply(layout)` from `beforePlace` and the resolver builds
the actual instance set against the live `LayoutCell`.

**Three-tier precedence** for picking up grouping intent (older
discussion — still accurate):

1. Sidecar YAML — explicit, machine-editable, highest priority.
2. Pycell-declared (existing `addStack(...)` calls work as implicit
   groups for back-compat).
3. Naming-convention fallback (`x<kind>[_<gid>]_<role>`) — used by the
   GUI to auto-suggest peers when "Add Selection" is clicked.

### What `apply()` emits

For each visible group with corresponding YAML keys:

| YAML | Emitted call |
|------|--------------|
| `placement.stack: true` | `CellGroup = layout.addStack(name, instances)` |
| `ports: [{layer, net, side, style, options}]` | `layout.addPortOnEdge(...)` |
| `routes: [{kind: connection, ...}]` | `layout.addRouteConnection(net, layer, location, options)` |
| `routes: [{kind: orthogonal, parent?, layer1, layer2, ...}]` | `CellGroup.addOrthogonalConnectivityRoute(...)` or layout-level variant |

`apply()` returns `{group_name: CellGroup}` so the pycell can chain
extra routing/sizing on top.

## Shipped phases (summary)

- **Phase 1** — Layout viewer, cic-gui parity. `F` fit, `Z`/`Ctrl+Z`
  zoom, right-drag zoom-to-area, wheel/arrows pan, `Ctrl+wheel` zoom,
  `T` toggle layers, `Shift+R` reload (plus `QFileSystemWatcher`),
  `QSettings` persistence keyed by tech.
- **Phase 2** — Schematic pane via `eda/xschem.py` parse extensions
  (L/B/P/A/T/N), `sym_loader` cache, cross-probing with `(kind, gid)`
  highlights in both panes, `e`/`Ctrl+E` hierarchy nav.
- **Phase 2.5 / 4b** — Net highlighting; connectivity panel with
  flight lines for split nets and shorts; "Limit to active group"
  filter. `LayoutCell.checkConnectivity` extended to return
  `components_bbox`.
- **Phase 3 / 4d** — Pycells opt in with `cicpy.groups.apply(layout)`
  in `beforePlace`. Verified end-to-end on `LELOTEMP_CMP`: GUI-authored
  YAML produces the same `addStack` the hand-written pycell did.
- **Phase 4a** — Planning groups: sidecar YAML, group panel
  (checkable, solo/mute), member filter dims/hides non-members in both
  panes, "Add Selection" pulls naming-convention peers.
- **Phase 4c** — Route authoring: right-click an open net in the
  connectivity panel → "Plan route…" writes a structured route entry
  to the active group's YAML.
- **Phase 4-ext** — Schematic rename for placement reordering.
  Multi-select on the schem pane (shift-click + lasso), Rename button
  in the groups panel. `eda/xschem.Component` round-trips byte-identical
  for unmodified components. Bus suffix `[3:0]` preserved across
  rename. `.sch.bak` written before rewrite.
- **Latest (`be2a743`)** — Lasso selection in the schem pane, nets
  panel listing every `lab=` net with active-group filter and substring
  search, `apply()` consumes per-group `ports`.
- **Latest (`ea4d804` + follow-up)** — Layout hierarchy metadata and
  rendering. `.cic` JSON now carries `cellgroups` metadata
  (`CellGroup` / `StackGroup` / `RouteBundle` bboxes and ports), and
  the layout scene can collapse rendering to CellGroups, Stacks,
  RouteBundles, or Full geometry.
- **Latest (`e55cb7a` / `4f84b98`)** — Cellgroup single ownership.
  `CellGroup` / `StackGroup` now form a real layout-only ownership tree
  while `.cic` JSON keeps flat physical children plus `cellgroups`
  metadata for GUI hierarchy.
- **Latest** — Apparent layout hierarchy / group macro routing.
  `CellGroup` / `StackGroup` can auto-export boundary ports for nets
  crossing the group boundary, top-level connectivity routes prefer
  those ports, and `includeInstances` remains the explicit direct
  terminal escape hatch.
- **Latest (§7)** — TerminalAccess removed. The
  `Instance.getTerminalAccess` / `TerminalAccess` path that walked
  cell-internal connected geometry is gone; pin discovery now reads
  `port.get(layer)` directly. `Cell.findAllRectangles` gained the
  `instname:terminal` path semantics from C++ ciccreator so
  `addDirectedRoute("M1", net, "xn_diode1:D-xn_diode1:G")` resolves
  correctly. `routeDiodeConnected` and `routeDummyTerminals` now emit
  `addDirectedRoute` calls (the dummy variant became a single M1
  strap rect across each filler in `fa33d25`); `routeParallel` /
  `routeMirror` use `port.get(layer)` for pin discovery and keep the
  trunk + bundle shape that backs the §1 boundary-port contract. The
  supported routing primitives are now the only routing primitives:
  `addConnectivityRoute`, `addOrthogonalConnectivityRoute`, and
  `addDirectedRoute`.
- **Latest (`5708abb` / `911231f` / `3d8feeb`)** — `accessLayer`
  deprecation and boundary-suppression fix. Removed the `accessLayer`
  argument from `addOrthogonalConnectivityRoute` (and the cellgroup
  wrappers + the `apply()` YAML schema): pin geometry follows the
  device's exposed port layer and the route engine handles the cuts.
  Removed `requireLayer` from `getNodeAccessRects`. Boundary-port
  suppression in `_groupNodeAccessRects` is now conditional on the
  group having internal routing (`routedNets()`) for the net —
  without internal routing, member pins are no longer hidden behind a
  single boundary port and the parent route engine ties every member.
  `_make_boundary_port` keeps the source rect's actual layer instead
  of coercing to the requested layer. **LELOTEMP_CMP went from
  shorts=1 opens=5 → shorts=1 opens=0**; only the pre-existing
  VDD_1V8/VSS placement short remains.

## What's next

Apparent layout hierarchy is now in place. Remaining work is mostly GUI
polish and schema documentation.

### 1. Apparent layout hierarchy / group macro routing (shipped)

The schematic should remain a human-readable analog picture with diff
pairs, mirrors, switches, startup devices, and bias branches visible in
one context. The layout can still be refactored into small, well-defined
chunks that are easier to route. Treat those chunks as **layout-only
macros**: `CellGroup`, `StackGroup`, current mirror groups, diff-pair
groups, and switch groups can own physical instances, route local
internals, and expose intentional **boundary ports** to top-level
routing.

**Contract:** top-level routing should prefer exported group boundary
ports. The group is responsible for its internal routing; parent routes
should not usually rediscover every transistor terminal inside the
group. Direct terminal discovery remains useful as an explicit escape
hatch for debug or special routes.

**Boundary ports:** auto-detect nets that cross the group boundary:
at least one member instance terminal inside the group, and at least one
terminal or top-level port outside the group. Internal-only nets stay
inside the group. Boundary ports should prefer completed local
`RouteBundle` access; if no routed bundle exists yet, fall back to a
representative real instance terminal access.

**Completion check:** after local group routing, run a group-scoped
connectivity check for internal-only nets. For now this should warn
only, not fail `sch2mag`, so placement/routing can still be iterated.

**Implemented:**
1. `LayoutCell.getNodeAccessRects(...)` collects
   group boundary ports or direct instance terminal access for a net.
2. `CellGroup.exportBoundaryPorts(...)` and `StackGroup` auto-export
   one selected boundary port from routed local geometry or
   representative terminal access. Route-style selectors such as
   `onTopLeft`, `onTopRight`, `onBottomLeft`, and `onBottomRight`
   choose which access point is exposed. Transistor bulk access is not
   mixed into normal D/G/S boundary ports; use `bulk` or `terminal=B`
   when a body connection is intentionally requested.
3. `addConnectivityRoute`, `addOrthogonalConnectivityRoute`,
   and `addRouteConnection` to use group ports by default and direct
   instance terminals only when explicitly scoped.
4. Stackgroup tests cover boundary-net export, hidden internal nets,
   direct-terminal escape, and warning-only internal completion.

### 2. Port authoring dialog (carried over from `be2a743` TODO)

`apply()` already emits `addPortOnEdge` from a `ports: [...]` list, but
the user has to hand-edit YAML to add one. Add a "Add port…" action in
the groups panel: dialog with layer (combo from tech), net (combo from
the cell's nets), side (N/S/E/W), style, options. Writes a port entry
to the active group's YAML.

### 3. Tools menu: bake YAML → explicit Python (carried over)

For users who want to graduate a pycell off `apply()`, add a Tools menu
action that dumps the resolved group set as the equivalent
`addStack` / `addPortOnEdge` / `addRouteConnection` Python calls into
the pycell scaffold. One-shot generator, not a live binding.

### 4. Phase 4-ext rename — remaining open issues

- **`T {label} ...` text references** — if a schematic has explicit
  text labels naming a renamed component (e.g. an annotation
  `T {xfoo} ...`), they aren't updated. Detect by literal-string match
  and prompt before rewriting; skip if ambiguous.
- **Net labels referencing components** — same shape: a wire `lab=`
  may name a component. Currently untouched. Decide whether to update
  or warn.

`xfoo[3:0]` bus suffix preservation and `.sch.bak` undo are already in.

### 5. Open vocabulary / schema items

- **Group `kind` vocabulary** — current freeform string. Lock down
  `mirr | diff | casc | stack | xcpl` and document `role` semantics
  per kind, so the naming-convention auto-suggestion is predictable.
- **`addGroup(...)` pycell helper** — still not implemented. Decide
  whether it's worth adding given that sidecar YAML + `apply()`
  cover the same ground. Likely **drop** unless a concrete pycell
  needs it; revisit only if the case appears.
- **Sidecar YAML schema doc** — the schema exists de facto in
  `groups.py` (`Group.from_dict` / `to_dict`). Write a short reference
  in `docs/groups.md` so users can hand-edit confidently. Include the
  full `placement` / `ports` / `routes` keys that `apply()` consumes.

### 6. Single-ownership refactor for cellgroups

CellGroups are currently a *logical overlay*: they live in
`layout.cellgroups` (separate from `layout.children`) and re-parent
their member instances into `stack.children` while the same instances
remain in `layout.children`. Two views of the same data, kept in sync
manually.

The cleaner model — and what `ciccreator/cic-core` does in C++ — is
single ownership: when `cg.addStack(name, instances)` runs, *move*
those instances out of `layout.children` into `stack.children`.
`layout.children` then holds ungrouped instances + cellgroups; each
instance is visited exactly once by tree-walkers (toJson, scene render,
calcBoundingRect, routing passes).

**Why defer:** at least 8+ flat-iteration sites in `layoutcell.py`
plus `magicprinter.py`, `routering.py`, `instance.py` do
`for c in self.children: if c.isInstance(): ...` and would silently
miss grouped instances. Each needs to be audited and switched to a
recursive walk (or to a new `getInstances()` helper). Mechanical but
broad — wants its own commit + full test sweep, not bundled into a
GUI feature.

**Status:** shipped. `LayoutCell.iterPlacementChildren()` /
`iterInstances()` provide a recursive, de-duplicated walk across
`children` and `cellgroups`; `makeCellGroup()` now registers groups as
layout children; and `StackGroup.addInstance()` moves stacked devices
out of their previous parent before owning them. `.cic` JSON stays flat
for physical children while retaining `cellgroups` metadata for GUI
hierarchy.

This shipped refactor is the foundation for apparent layout hierarchy:
groups now have real ownership, but they still need a boundary-port
contract before they behave like routed layout macros.

**Plan:**
1. Done — add `LayoutCell.iterInstances()` helper that recurses
   through `children` and `cellgroups` once.
2. Done — replace core flat instance lookup sites with the helper.
3. Done — move ownership in `CellGroup.addStack` /
   `StackGroup.addInstance`: pop the instance from
   `layout.children` (and any other ancestor's `children`) before
   `stack.add(inst)`.
4. Done — preserve flat physical JSON output while keeping `cellgroups`
   metadata for GUI hierarchy; revisit full hierarchical JSON only
   after downstream readers are audited.
5. Done — run `tests/stackgroups`, `tests/sch2mag`, and `tests/spi2mag`
   end to end. LVS-clean LELOTEMP_CMP regen is the canary.

### 7. Remove `TerminalAccess` / `getTerminalAccess` (shipped)

`TerminalAccess` (`core/instance.py`) and the various
`getTerminalAccess(...)` paths into `cellgroup.py`, `layoutcell.py`,
and `routes/build_route_examples.py` were intended as a "find the legal
metal pin on this device terminal at layer X" helper. In practice the
apparent-layout-hierarchy work (§1) ended up using terminal access as a
backdoor for routing — picking access rectangles inside groups that
should have gone through their boundary ports, and re-discovering
geometry that `directedRoute` already produces correctly.

That violates the macro contract: groups own their internal routing
and expose boundary ports; outside the group, callers should route to
those ports, not introspect terminals. Where a parent route really
does need a specific transistor pin, `addDirectedRoute(layer, net,
route, options)` already names the start/stop endpoints explicitly and
honours the access-layer rules.

**Routing-API principle (applies beyond this section):**
The supported routing primitives are
`addConnectivityRoute`, `addOrthogonalConnectivityRoute`, and
`addDirectedRoute` (the last is the emergency hatch for explicit
pin-to-pin connections). New routing helpers should be **compositions
of these primitives**, not new code paths into the route engine. If a
helper feels like it needs a fourth route function, that is a signal
the abstraction is wrong — fold it into one of the three.

**Plan:**

1. **Step 1 — Fallback in `_directNodeAccessRects`** (cheap).
   Remove `layoutcell.py:273-278` `getTerminalAccess` fallback. After
   boundary ports (§1) and direct `port.get(layer)` fail, the only
   answer is `addDirectedRoute`; the terminal-access fallback was the
   loophole that let routes skip the boundary-port contract.
2. **Step 2 — Fallback in `representativeAccessRects`** (cheap).
   Replace `cellgroup.py:639-647` access lookup with `port.get(layer)`;
   return empty if absent.
3. **Step 2.5 — Port C++ `findAllRectangles` path semantics**
   (prerequisite for Steps 3–5). cicpy's current `Cell.findAllRectangles`
   only iterates direct children matching `child.name`; the
   `instname:terminal` syntax used by the C++ tool's
   `addDirectedRoutes` JSON does **not** work in Python today. Port the
   ciccreator behavior from `cic-core/src/core/cell.cpp:90-180`:
   comma-split regex, `:`-recurse into instances by `instanceName`,
   local port lookup on bare names, plus the auxiliary
   immediate-child-instance-port match. With that, route strings like
   `"xn_diode1:D-xn_diode1:G"` resolve correctly and Steps 3–5 can use
   `addDirectedRoute` as the rewrite target.
4. **Step 3 — `routeDiodeConnected`** (real work). Rewrite as a loop
   of `addDirectedRoute(layer, net, f"{name}:D-{name}:G")` calls (one
   per diode-connected instance). Keep the diode-connect detection
   logic (drain_net == gate_net) — only the geometry construction
   changes.
5. **Step 4 — `routeDummyTerminals`** (real work). Rewrite as three
   `addDirectedRoute` calls per dummy device: `B-D` mid, `B-S` side,
   `D-S` vertical, all on `M1`.
6. **Step 5 — `routeParallel` / `routeMirror`** (real work).
   Collapse the trunk-construction path to `addConnectivityRoute`
   calls scoped by `includeInstances` to the stack's members. The
   `RouteBundle` then exposes its boundary port as a post-pass that
   harvests the produced route geometry on the bundle's edge layer
   and wraps it as the group's exported port (preserves §1).
7. **Step 6 — Delete `TerminalAccess` / `Instance.getTerminalAccess`**.
   Strip imports from `tests/stackgroups/test_stackgroups.py` and
   rewrite those tests to assert against routed geometry / boundary
   ports. Remove `tests/routes/build_route_examples.py:150` use.
8. **Step 7 — Documentation**. Update
   `tests/sch2mag/lelo_temp_sky130a/AGENTS.md` and
   `tests/routes/routes.md` to drop `getTerminalAccess` from the
   "preferred API" guidance and point at the three primitives plus
   boundary ports.

Each step ends with the full test sweep (`tests/stackgroups`,
`tests/sch2mag/lelo_temp_sky130a`, `tests/spi2mag`, `tests/routes`).
LVS-clean LELOTEMP_CMP regen is the canary. Commit per green step,
not all at once.

**Why now:** the boundary-port contract from §1 only holds if there
isn't a parallel terminal-access path that bypasses it. Leaving
`TerminalAccess` in the codebase invites future routing code to route
through it again and re-introduce the bug.

### 8. accessLayer deprecation and boundary-port suppression (shipped)

After §7 removed `TerminalAccess`, `accessLayer` was the remaining
hand-fed layer hint that fought the device geometry: every sky130A
D/G/S port lives on cicpy M2 (alias for `m1`), so callers passing
`accessLayer="M1"` couldn't resolve without the deleted
connected-geometry walk.

**Shipped:**

- `5708abb` — drop `accessLayer` argument from
  `LayoutCell.addOrthogonalConnectivityRoute`, the `CellGroup` /
  `StackGroup` wrappers, and the `apply()` YAML schema. Drop
  `requireLayer` from `getNodeAccessRects` /
  `_directNodeAccessRects`. `_make_boundary_port` keeps the source
  rect's actual layer instead of coercing to the requested one. Pin
  geometry follows the device port; the route engine inserts the
  cuts. Update `LELOTEMP_CMP.py` and the four doc surfaces
  (pycell.md, routes.md, layout.md, tests/routes/routes.md).
- `911231f` (later reverted in `3d8feeb`) — short-lived M1 filter in
  `addPowerConnection`. Replaced by the proper fix below.
- `3d8feeb` — only suppress group member pins in
  `_groupNodeAccessRects` when the group reports the net via
  `routedNets()`. Without internal routing the boundary port stands
  in for one rep pin and member pins must still feed the parent
  route engine — suppression isolated them. Test stub updated:
  `bulk_top_rects` for VSS now legitimately includes both the source
  and bulk pins because the bulk_group has no internal VSS routing.

**Verified on `LELOTEMP_CMP`:**

| | shorts | opens | components |
|---|---|---|---|
| pre-§7 baseline (TerminalAccess) | 1 | 5 | 58 |
| post-§7 / pre-deprecation        | 1 | 5 | 58 |
| `5708abb` (deprecate)            | 1 | 6 | 76 |
| `911231f` (M1 filter)            | 1 | 4 | 49 |
| `3d8feeb` (conditional suppress) | **1** | **0** | **35** |

The remaining short is a pre-existing `VDD_1V8`/`VSS` overlap from
the placement (3050 rects, no routes attached) — separate from the
routing surface this section cleaned up.

### 9. Acceptance / smoke tests

Manual smoke runs only so far. Consider a tiny PNG snapshot test for
the layout pane on `LELOTEMP_CMP` to catch regressions in `style.py` /
`layout_scene.py` rendering. Skip if it's more infra than payoff.

### 10. Open: cell connectivity status after §8

End-to-end check across the four LELOTEMP cells (IP repo, post §8):

| Cell | shorts | opens | notes |
|---|---|---|---|
| LELOTEMP_CMP      | 0 | 0 | clean |
| LELOTEMP_START    | 1 | 0 | `addRouteConnection(VSTART3, M4, bottom)` shorts VCP/VO/VSS/VSTART3 |
| LELOTEMP_CASCBIAS | 0 | 6 | VSS / VBNT / VCN / VCP / VBP4 / VDD_1V8 each split |
| LELOTEMP_CCMP     | 2 | 2 | `IBP_1U<0>` M5 trunk shorts to VSS, plus a `CMPO/VDD_1V8` placement short |

§8's conditional suppression resolved LELOTEMP_CMP cleanly but loosened
suppression for cells without internal group routing (START, CASCBIAS,
CCMP) — more member pins surface, and `addRouteConnection` /
`addOrthogonalConnectivityRoute` create more route geometry per net,
which in dense areas overlaps and shorts (START's VSTART3 case) or
fails to fully merge (the opens on CASCBIAS).

Possible directions:

- Apply the same conditional rule to `addRouteConnection`'s lookup
  surface (it shares `getNodeAccessRects`); confirm whether the
  trunks really need every member pin or whether the existing pycell
  intent is "first matching pin wins". If the latter, an
  options-driven "one rep pin per group" mode would match the
  LELOTEMP_START intent without re-introducing the §8 fragmentation.
- Audit `_make_boundary_port` keeping the source layer instead of
  coercing — `addRouteConnection` may rely on the boundary rect being
  on the route's verticalLayer for trunk placement.
- Pre-existing `LELOTEMP_CMP VDD_1V8/VSS` placement short
  (`rects=3050 routes=none`) is independent — overlap from the n-well
  tap or power-ring geometry, separate from the routing pipeline.

## Reference files

- `src/cicpy/gui/*.py`
- `src/cicpy/groups.py`
- `src/cicpy/eda/xschem.py`
- `src/cicpy/printer/svgprinter.py` (original blueprint for scene walker)
- `lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.{cic,sch,py,sym,mag}`
  — primary test case; everything above has been verified end-to-end on it.
