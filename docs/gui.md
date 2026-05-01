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

`Ctrl`/`Cmd` + wheel also zooms; `Shift` + wheel pans horizontally.

## What's in the window

- **Cell list** (top-left) — every cell in the loaded design + dependency libraries. Row change loads that cell into the layout pane.
- **Layer list** (middle-left) — every layer from the tech file. Pin layers and `TXT` are visible by default; non-pin implant layers default off. Each row has a color swatch icon and a checkbox for visibility. State persists across sessions per tech via `QSettings`.
- **Route list** (bottom-left) — routes in the selected cell. Each row is checkable, and entries prefixed with `*` touch or overlap another differently named route on the same layer. Same-name route contacts are not marked.
- **Layout pane** (right) — the cell rendered into a `QGraphicsScene`. Y-flipped to match conventional layout view (Y grows up).
- **Status bar** — cursor coordinates in technology units (Ångström) and µm.

Route labels and top-cell port labels are rendered as `TXT` text. Sub-circuit port labels are suppressed to avoid clutter; use the route list and top-level port labels for the first-level view.

Window geometry, splitter sizes, last-opened cell, and per-layer visibility are all persisted.
