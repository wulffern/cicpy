# gui

`cicpy gui` opens a Qt viewer on a `.cic` file — the Python successor to ciccreator's C++ `cic-gui`. Phase 1 ships a layout-only viewer; a side-by-side schematic pane is planned for Phase 2 (see [`gui_plan`](/cicpy/gui_plan)).

## Install

PySide6 is an optional dependency, gated behind the `gui` extra:

```sh
pip install -e '.[gui]'
```

## Run

```sh
cicpy gui path/to/CELL.cic
```

The tech file and dependency libraries are auto-discovered from the IP layout — no flags required for the common case.

### Auto-discovery

- **Tech file** — walks up from `CELL.cic` looking for `tech/cic/*.tech`. Picks the first match.
- **Dependency libraries** — walks up to find the IP's `config.yaml`, treats top-level keys with `remote:`/`revision:` entries as cicconf dependencies, and globs `<workspace>/<dep>/design/*.cic` for each. All discovered files are logged at INFO level on launch.
- **Sibling cells** — the selected `.cic` file's directory is indexed for `.cic`/`.cic.gz` files. Sibling files are loaded only when the currently loaded design references a missing instance cell, so opening `LELOTEMP_CCMP.cic` can pull in `LELOTEMP_CMP.cic` without loading every sibling.

### Overrides

```sh
cicpy gui CELL.cic --tech path/to/sky130A.tech \
                   --I extra_lib.cic \
                   --no-auto-libs
```

- `--tech FILE` — override auto-discovery.
- `--I FILE` (repeatable) — merge an extra `.cic` before opening (in addition to auto-discovered libs unless `--no-auto-libs`).
- `--no-auto-libs` — disable dependency-library auto-discovery.

## Keybindings

| Action | Binding |
|---|---|
| Fit cell to view | `F` |
| Zoom in | `Z` |
| Zoom out | `Ctrl+Z` (Cmd+Z on macOS) |
| Zoom to area | right-click drag |
| Pan | wheel, arrow keys |
| Toggle all layers | `T` |
| Toggle one layer | checkbox in layer list |
| Reload `.cic` | `Shift+R` (auto-reload also fires when the file changes on disk) |
| Descend hierarchy | click a schematic component, then `E` |
| Ascend hierarchy | `Ctrl+E` (Cmd+E on macOS) |
| Rerun spi2mag | `Ctrl+R` (Cmd+R on macOS) — runs `make` in the IP root by default |

`Ctrl`/`Cmd` + wheel also zooms; `Shift` + wheel pans horizontally.

## What's in the window

- **Cell list** (top-left) — every cell in the loaded design + dependency libraries. Row change loads that cell into the layout pane.
- **Layer list** (middle-left) — every layer from the tech file. Pin layers and `TXT` are visible by default; non-pin implant layers default off. Each row has a color swatch icon and a checkbox for visibility. State persists across sessions per tech via `QSettings`.
- **Route list** (bottom-left) — routes in the selected cell. Each row is checkable, and entries prefixed with `*` touch or overlap another differently named route on the same layer. Same-name route contacts are not marked.
- **Layout pane** (middle) — the cell rendered into a `QGraphicsScene`. Y-flipped to match conventional layout view (Y grows up).
- **Schematic pane** (right) — the matching XSchem `.sch` for the selected cell, if one is found next to the `.cic` or in the IP / dependency design directories. Hidden when no schematic exists.
- **Status bar** — cursor coordinates (Ångström + µm for layout, raw grid units for schematic).

## Rerunning spi2mag

`Ctrl+R` (or `Run → Rerun spi2mag`) shells out to `make` in the IP root (the directory containing `config.yaml`). Override either with `--rerun-cmd` and `--rerun-cwd` on the command line, or via `Run → Set rerun command…`. The `CICPY_GUI_RERUN_CMD` env var is also honoured.

`Run → Auto-rerun on .py change` (persistent in `QSettings`) watches the active cell's pycell `<CellName>.py` and triggers a debounced rerun whenever it changes on disk. The new `.cic` is then auto-reloaded by the existing `QFileSystemWatcher`. The intended loop is:

1. Edit `<CellName>.py` (or the sidecar `<CellName>.groups.yaml`)
2. Save
3. GUI reruns spi2mag
4. GUI reloads the freshly-written `.cic`

## Planning groups (Phase 4a)

Each cell can have a sidecar `<CellName>.groups.yaml` next to its `.py` describing **planning groups** — named subsets of instances. Membership can be enumerated explicitly (`members:`), pattern-matched (`member_regex:`), or net-driven (`member_nets:`); the resolver unions all three.

When any group is checked visible, both panes filter:
- Layout pane hides non-member top-level instances
- Schematic pane dims non-members to ~18% opacity (still legible context)

The bottom-left **Groups** panel manages them: `New` to create, right-click to rename / edit description / regex / members, `Add selection` to push the last-clicked schematic component (and its naming-convention peers) into the active group. The YAML is rewritten on every change.

```yaml
cell: LELOTEMP_OTAN
groups:
  - name: bias_chain
    description: Output stage bias mirror
    visible: true
    members: [xn_mirr_bias1, xn_mirr_bias2]
    member_regex: ['^xn_mirr_bias\d+']
```

Phases 4b–4f layer route/placement intent into the same YAML, where it'll be consumed by a `cicpy.groups.apply()` helper inside the pycell.

## Cross-probing

Click a component in the schematic pane. The GUI parses the instance name (e.g. `xn_mirr_load2` → group `xn_mirr_load`) and outlines every peer in both panes. The naming convention is `x<kind>[_<gid>]_<role>` — the `cIcSpice::Component.group()` regex captures the longest non-digit prefix.

`E` descends into the clicked component's underlying cell (`<symbol-basename>` looked up in `Design.cells`). `Ctrl+E` pops the history stack to ascend.

Route labels and top-cell port labels are rendered as `TXT` text. Sub-circuit port labels are suppressed to avoid clutter; use the route list and top-level port labels for the first-level view.

Window geometry, splitter sizes, last-opened cell, and per-layer visibility are all persisted.
