# gui plan

Status: **Phases 1, 2, 2.5, 3, 4a–4d, and 4-ext all shipped.** The viewer
is a working planning surface: layout + schematic panes, cross-probing,
hierarchy nav, planning groups, connectivity check with flight lines,
route authoring, schematic rename, and a nets panel with lasso select.
Pycells consume the YAML via `cicpy.groups.apply(layout)`. Remaining
work is a short tail of polish items — see [What's next](#whats-next).

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

## What's next

Short polish tail before declaring the GUI feature-complete. Roughly in
priority order:

### 1. Port authoring dialog (carried over from `be2a743` TODO)

`apply()` already emits `addPortOnEdge` from a `ports: [...]` list, but
the user has to hand-edit YAML to add one. Add a "Add port…" action in
the groups panel: dialog with layer (combo from tech), net (combo from
the cell's nets), side (N/S/E/W), style, options. Writes a port entry
to the active group's YAML.

### 2. Tools menu: bake YAML → explicit Python (carried over)

For users who want to graduate a pycell off `apply()`, add a Tools menu
action that dumps the resolved group set as the equivalent
`addStack` / `addPortOnEdge` / `addRouteConnection` Python calls into
the pycell scaffold. One-shot generator, not a live binding.

### 3. Phase 4-ext rename — remaining open issues

- **`T {label} ...` text references** — if a schematic has explicit
  text labels naming a renamed component (e.g. an annotation
  `T {xfoo} ...`), they aren't updated. Detect by literal-string match
  and prompt before rewriting; skip if ambiguous.
- **Net labels referencing components** — same shape: a wire `lab=`
  may name a component. Currently untouched. Decide whether to update
  or warn.

`xfoo[3:0]` bus suffix preservation and `.sch.bak` undo are already in.

### 4. Open vocabulary / schema items

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

### 5. Acceptance / smoke tests

Manual smoke runs only so far. Consider a tiny PNG snapshot test for
the layout pane on `LELOTEMP_CMP` to catch regressions in `style.py` /
`layout_scene.py` rendering. Skip if it's more infra than payoff.

## Reference files

- `src/cicpy/gui/*.py`
- `src/cicpy/groups.py`
- `src/cicpy/eda/xschem.py`
- `src/cicpy/printer/svgprinter.py` (original blueprint for scene walker)
- `lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.{cic,sch,py,sym,mag}`
  — primary test case; everything above has been verified end-to-end on it.
