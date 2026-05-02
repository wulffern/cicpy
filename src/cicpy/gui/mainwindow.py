######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import glob
import os
import re
import shutil

from PySide6.QtCore import QFileSystemWatcher, QProcess, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import cicpy as cic
from cicpy import groups as cicgroups
from cicpy.eda.xschem import Schematic
from .connectivity_panel import ConnectivityPanel
from .groups_panel import GroupsPanel
from .layout_scene import LayoutScene
from .layout_view import LayoutView
from .schem_scene import SchemScene
from .schem_view import SchemView
from .style import LayerStyle
from .sym_loader import SymbolLoader, discover_symbol_paths


SETTINGS_ORG = "cicpy"
SETTINGS_APP = "gui"


def _tech_name(techfile):
    if not techfile:
        return "default"
    return os.path.splitext(os.path.basename(techfile))[0]


def _layer_icon(color, size=14):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setPen(Qt.black)
    p.setBrush(color if color is not None else QColor(80, 80, 80))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):

    def __init__(self, cicfile, techfile, includes=(), rerun_cmd=None, rerun_cwd=None):
        super().__init__()
        self.cicfile = os.path.abspath(cicfile)
        self.techfile = os.path.abspath(techfile) if techfile else None
        self.includes = list(includes or [])
        self.tech_key = _tech_name(self.techfile)
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        # CLI > env > QSettings > default
        self.rerun_cmd = (
            rerun_cmd
            or os.environ.get("CICPY_GUI_RERUN_CMD")
            or self.settings.value("rerun_cmd", None, str)
            or "make"
        )
        self.rerun_cwd = rerun_cwd or self._discover_ip_root()

        self.rules = cic.Rules(self.techfile) if self.techfile else cic.Rules()
        self.style = LayerStyle(self.rules)
        self._restore_layer_visibility()

        self.design = self._load_design()

        self.scene = LayoutScene(self.design, self.style)
        self.view = LayoutView(self.scene)

        self.sym_loader = SymbolLoader(discover_symbol_paths(cicfile=self.cicfile))
        self.schem_scene = SchemScene(self.sym_loader)
        self.schem_view = SchemView(self.schem_scene)
        self._sch_search_paths = self._build_sch_search_paths()

        self.cell_list = QListWidget()
        self.layer_list = QListWidget()
        self.route_list = QListWidget()
        self.groups_panel = GroupsPanel()
        self.connectivity_panel = ConnectivityPanel()
        self._populate_cells()
        self._populate_layers()
        self._current_groupset = None
        self._connectivity_result = None

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.addWidget(self.cell_list, 1)
        left_layout.addWidget(self.layer_list, 1)
        left_layout.addWidget(self.route_list, 1)
        left_layout.addWidget(self.groups_panel, 1)
        left_layout.addWidget(self.connectivity_panel, 1)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.schem_view)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)
        self.setCentralWidget(self.splitter)

        self.setStatusBar(QStatusBar())

        self.setWindowTitle(
            f"cicpy gui — {os.path.basename(self.cicfile)} "
            f"[{self.tech_key}] (F=fit, Z=zoom, right-drag=zoom-area, "
            f"E=descend, Ctrl+E=ascend, Shift+R=reload, T=toggle layers)"
        )

        self.cell_list.currentRowChanged.connect(self._on_cell_changed)
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)
        self.route_list.itemChanged.connect(self._on_route_item_changed)
        self.view.cursorMoved.connect(self._on_cursor_moved)
        self.schem_view.cursorMoved.connect(self._on_cursor_moved_schem)
        self.schem_scene.componentClicked.connect(self._on_schem_component_clicked)
        self.schem_scene.selectionChanged.connect(self._on_schem_selection_changed)
        self.scene.instanceClicked.connect(self._on_layout_instance_clicked)
        self.groups_panel.filterChanged.connect(self._on_groups_changed)
        self.groups_panel.addSelectionRequested.connect(self._on_add_selection_to_group)
        self.groups_panel.renameSchemSelectionRequested.connect(self._rename_schem_selection)
        self.connectivity_panel.runRequested.connect(self.run_connectivity_check)
        self.connectivity_panel.rowActivated.connect(self._on_connectivity_row)
        self.connectivity_panel.planRouteRequested.connect(self._plan_route_dialog)

        QShortcut(QKeySequence("Shift+R"), self, activated=self.reload)
        QShortcut(QKeySequence("T"), self, activated=self.toggle_all_layers)
        QShortcut(QKeySequence("E"), self, activated=self._descend)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._ascend)
        QShortcut(QKeySequence("Meta+E"), self, activated=self._ascend)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.rerun_spi2mag)
        QShortcut(QKeySequence("Meta+R"), self, activated=self.rerun_spi2mag)
        self._cell_history = []
        self._last_clicked_comp = None
        # spi2mag rerun infrastructure
        self._rerun_proc = None
        self._py_watcher = QFileSystemWatcher(self)
        self._py_watcher.fileChanged.connect(self._on_py_changed)
        self._current_py = None
        self._auto_rerun = self.settings.value("auto_rerun", False, bool)
        self._rerun_debounce = QTimer(self)
        self._rerun_debounce.setSingleShot(True)
        self._rerun_debounce.setInterval(500)
        self._rerun_debounce.timeout.connect(self.rerun_spi2mag)
        # menu
        self._build_menu()

        self.watcher = QFileSystemWatcher(self)
        self._watch_files()
        self.watcher.fileChanged.connect(self._on_file_changed)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(250)
        self._reload_timer.timeout.connect(self.reload)

        self._restore_window_state()

        last = self.settings.value("last_cell", "", str)
        if last and last in self.design.cells:
            row = self.design.cellnames.index(last)
            self.cell_list.setCurrentRow(row)
        elif self.cell_list.count():
            self.cell_list.setCurrentRow(0)

    # -- loading --------------------------------------------------------

    def _load_design(self):
        d = cic.Design()
        d.fromJsonFilesWithDependencies(self.cicfile, self.includes)
        return d

    def _populate_cells(self):
        self.cell_list.clear()
        for name in self.design.cellNames():
            self.cell_list.addItem(name)

    def _populate_layers(self):
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for name in self.style.layer_names():
            item = QListWidgetItem(name)
            item.setIcon(_layer_icon(self.style.color(name)))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if self.style.is_visible(name) else Qt.Unchecked
            )
            self.layer_list.addItem(item)
        self.layer_list.blockSignals(False)

    def _populate_routes(self):
        self.route_list.blockSignals(True)
        self.route_list.clear()
        connected_routes = self.scene.connected_route_names()
        for key in self.scene.route_names():
            label = self.scene.route_label(key)
            if key in connected_routes:
                label = f"* {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            if key in connected_routes:
                item.setToolTip("Touches or overlaps another route on the same layer")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if self.scene.is_route_visible(key) else Qt.Unchecked
            )
            self.route_list.addItem(item)
        self.route_list.setVisible(self.route_list.count() > 0)
        self.route_list.blockSignals(False)

    # -- callbacks ------------------------------------------------------

    def _on_cell_changed(self, row):
        if row < 0 or row >= self.cell_list.count():
            return
        name = self.cell_list.item(row).text()
        cell = self.design.getCell(name)
        # Persist any pending edits to the previous cell's groupset.
        self._save_groupset_if_dirty()
        self.scene.set_cell(cell)
        self._populate_routes()
        self.scene.apply_visibility()
        self.view.fit()
        self._load_schematic_for(name)
        self._load_groupset_for(name, cell)
        self._apply_group_filter()
        self._watch_py_for(name)
        self.settings.setValue("last_cell", name)

    def _on_layer_item_changed(self, item):
        name = item.text()
        new_vis = item.checkState() == Qt.Checked
        if self.style.is_visible(name) == new_vis:
            return
        self.style.set_visible(name, new_vis)
        self.scene.apply_visibility()
        self.settings.setValue(f"layers/{self.tech_key}/{name}", new_vis)

    def _on_route_item_changed(self, item):
        key = item.data(Qt.UserRole)
        if not key:
            return
        new_vis = item.checkState() == Qt.Checked
        if self.scene.is_route_visible(key) == new_vis:
            return
        self.scene.set_route_visible(key, new_vis)
        self.scene.apply_visibility()

    def _on_cursor_moved(self, x, y):
        # Layout coords are in technology units (Ångström). 10 Å = 1 nm.
        self.statusBar().showMessage(
            f"layout: x={x:.0f} y={y:.0f}  ({x/10000:.3f},{y/10000:.3f}) µm"
        )

    def _on_cursor_moved_schem(self, x, y):
        # Schematic coords are xschem grid units; just show raw values.
        self.statusBar().showMessage(f"schem: x={x:.0f} y={y:.0f}")

    def _on_schem_component_clicked(self, comp):
        self._last_clicked_comp = comp
        name = (comp.name() or "").strip()
        prefix = comp.group()
        members = self.schem_scene.highlight_group_by_prefix(prefix) if prefix else []
        # Mirror highlight in layout: match by instanceName prefix.
        layout_matched = []
        if prefix:
            layout_matched = self.scene.highlight_instance_prefix(prefix)
        elif name:
            layout_matched = self.scene.highlight_instances([name])
        if not name:
            return
        bits = [f"selected {name}"]
        if prefix:
            bits.append(f"schem group '{prefix}': {len(members)}")
        if layout_matched:
            bits.append(f"layout: {len(layout_matched)}")
        self.statusBar().showMessage(" — ".join(bits), 4000)

    def _on_schem_selection_changed(self, comps):
        if not comps:
            return
        names = [c.name() or "?" for c in comps]
        head = ", ".join(names[:4])
        if len(names) > 4:
            head += f", … ({len(names)} total)"
        self.statusBar().showMessage(f"selected: {head}", 3000)

    def _on_layout_instance_clicked(self, instance_name):
        import re
        m = re.match(r"^(x\D+)", instance_name, re.I)
        prefix = m.group(1) if m else instance_name
        # Highlight in both panes
        layout_matched = self.scene.highlight_instance_prefix(prefix)
        schem_members = (
            self.schem_scene.highlight_group_by_prefix(prefix) if prefix else []
        )
        # Track for hierarchy descend: prefer exact-name comp, else any peer
        comp = None
        grp = self.schem_scene._components_by_name.get(instance_name)
        if grp is not None:
            comp = grp.data(1)
        if comp is None and schem_members:
            grp = self.schem_scene._components_by_name.get(schem_members[0])
            if grp is not None:
                comp = grp.data(1)
        self._last_clicked_comp = comp
        bits = [f"layout: {instance_name}"]
        if prefix:
            bits.append(f"group '{prefix}'")
        bits.append(f"layout peers: {len(layout_matched)}")
        bits.append(f"schem peers: {len(schem_members)}")
        self.statusBar().showMessage(" — ".join(bits), 4000)

    def _on_file_changed(self, path):
        # QFileSystemWatcher drops the path when an editor / spi2mag
        # rewrites the file via replace-in-place; re-add defensively so
        # subsequent rewrites still fire change events.
        try:
            if os.path.exists(path) and path not in self.watcher.files():
                self.watcher.addPath(path)
        except Exception:
            pass
        self._reload_timer.start()

    # -- spi2mag rerun -------------------------------------------------

    def _discover_ip_root(self):
        d = os.path.dirname(os.path.abspath(self.cicfile))
        for _ in range(8):
            if os.path.isfile(os.path.join(d, "config.yaml")) and \
               (os.path.islink(os.path.join(d, "tech")) or os.path.isdir(os.path.join(d, "design"))):
                return d
            new_d = os.path.dirname(d)
            if new_d == d:
                break
            d = new_d
        return os.path.dirname(os.path.abspath(self.cicfile))

    def _build_menu(self):
        menu_bar = self.menuBar()
        run_menu = menu_bar.addMenu("&Run")
        a_rerun = QAction("Rerun spi2mag", self)
        a_rerun.setShortcut(QKeySequence("Ctrl+R"))
        a_rerun.triggered.connect(self.rerun_spi2mag)
        run_menu.addAction(a_rerun)
        a_auto = QAction("Auto-rerun on .py change", self, checkable=True)
        a_auto.setChecked(bool(self._auto_rerun))
        a_auto.toggled.connect(self._set_auto_rerun)
        run_menu.addAction(a_auto)
        a_cmd = QAction("Set rerun command…", self)
        a_cmd.triggered.connect(self._edit_rerun_cmd)
        run_menu.addAction(a_cmd)

    def _set_auto_rerun(self, on):
        self._auto_rerun = bool(on)
        self.settings.setValue("auto_rerun", self._auto_rerun)
        state = "on" if self._auto_rerun else "off"
        self.statusBar().showMessage(f"auto-rerun {state}", 2000)

    def _edit_rerun_cmd(self):
        from PySide6.QtWidgets import QInputDialog
        cur = self.rerun_cmd
        new, ok = QInputDialog.getText(
            self, "Rerun command", "Shell command:", text=cur)
        if ok and new.strip():
            self.rerun_cmd = new.strip()
            self.settings.setValue("rerun_cmd", self.rerun_cmd)
            self.statusBar().showMessage(f"rerun command: {self.rerun_cmd}", 3000)

    def _watch_py_for(self, cell_name):
        # Stop watching the previous .py
        files = self._py_watcher.files()
        if files:
            self._py_watcher.removePaths(files)
        # The pycell sits next to the .cic in IP convention.
        py_path = os.path.join(
            os.path.dirname(self.cicfile), f"{cell_name}.py")
        if os.path.isfile(py_path):
            self._py_watcher.addPath(py_path)
            self._current_py = py_path
        else:
            self._current_py = None

    def _on_py_changed(self, path):
        # Some editors replace-on-save; re-add to keep watching.
        if os.path.exists(path):
            self._py_watcher.addPath(path)
        self.statusBar().showMessage(
            f"{os.path.basename(path)} changed"
            + (" — rerunning…" if self._auto_rerun else " — Ctrl+R to rerun"),
            3000,
        )
        if self._auto_rerun:
            self._rerun_debounce.start()

    def rerun_spi2mag(self):
        if self._rerun_proc is not None and \
                self._rerun_proc.state() != QProcess.NotRunning:
            self.statusBar().showMessage("rerun already in progress", 2000)
            return
        proc = QProcess(self)
        proc.setWorkingDirectory(self.rerun_cwd)
        proc.setProgram("/bin/sh")
        proc.setArguments(["-c", self.rerun_cmd])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda p=proc: self._on_rerun_output(p))
        proc.finished.connect(
            lambda code, st, p=proc: self._on_rerun_finished(p, code, st))
        self._rerun_proc = proc
        self.statusBar().showMessage(
            f"rerun: {self.rerun_cmd} (cwd={self.rerun_cwd})")
        proc.start()

    def _on_rerun_output(self, proc):
        data = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        last = data.rstrip().splitlines()[-1] if data.strip() else ""
        if last:
            self.statusBar().showMessage(f"rerun: {last}", 0)

    def _on_rerun_finished(self, proc, code, status):
        ok = code == 0
        msg = f"rerun {'OK' if ok else f'failed (exit {code})'}"
        self.statusBar().showMessage(msg, 5000)
        self._rerun_proc = None

    # -- schematic rename (Phase 4-ext) --------------------------------

    def _rename_schem_selection(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        comps = self.schem_scene.selected_components()
        if not comps:
            QMessageBox.information(
                self, "Rename", "Shift-click components in the schematic first.")
            return
        sch_path = getattr(self, "_current_sch_path", None)
        if not sch_path:
            QMessageBox.warning(self, "Rename", "No .sch file loaded.")
            return
        prefix, ok = QInputDialog.getText(
            self, "Rename selection",
            f"New prefix (will become <prefix>1..{len(comps)}):",
        )
        if not ok or not prefix.strip():
            return
        prefix = prefix.strip()
        # Check for name collisions across the schematic.
        existing = set(self.schem_scene._components_by_name.keys())
        # Remove names of the selected comps from `existing` (they'll be replaced)
        for c in comps:
            existing.discard(c.name() or "")
        new_names = []
        for i, comp in enumerate(comps, start=1):
            old = comp.name() or ""
            m = re.match(r"^(.*?)(\[[^\]]+\])?$", old)
            bus = m.group(2) or "" if m else ""
            new_names.append(f"{prefix}{i}{bus}")
        for n in new_names:
            if n in existing:
                QMessageBox.warning(
                    self, "Rename",
                    f"Name '{n}' already exists in the schematic.")
                return
        # Confirm
        sample = ", ".join(f"{c.name() or '?'} → {n}"
                           for c, n in list(zip(comps, new_names))[:4])
        if len(comps) > 4:
            sample += f", … ({len(comps)} total)"
        if QMessageBox.question(
            self, "Confirm rename",
            f"Rename:\n  {sample}\n\nWrites {os.path.basename(sch_path)} "
            f"(.bak saved). Re-run spi2mag afterwards.",
        ) != QMessageBox.Yes:
            return
        # Backup
        try:
            shutil.copy2(sch_path, sch_path + ".bak")
        except Exception as exc:
            QMessageBox.warning(self, "Rename", f"Backup failed: {exc}")
            return
        # Apply rename in-memory and flag those components as modified so we
        # only regenerate the lines we actually changed (preserves multi-line
        # property formatting on untouched ones).
        for comp, new in zip(comps, new_names):
            comp.properties["name"] = new
            comp._cicpy_modified = True
        try:
            with open(sch_path, "w") as f:
                for child in self.schem_scene.schematic.children:
                    if (child.__class__.__name__ == "Component"
                            and getattr(child, "_cicpy_modified", False)):
                        f.write(child.to_sch_line())
                    else:
                        f.write(child.ss)
        except Exception as exc:
            QMessageBox.critical(self, "Rename", f"Write failed: {exc}")
            return
        self.statusBar().showMessage(
            f"renamed {len(comps)} components — re-run spi2mag (Ctrl+R)",
            5000,
        )
        # Reload schematic so the new names show up.
        cell_name = self.cell_list.currentItem().text() if self.cell_list.currentItem() else ""
        if cell_name:
            self._load_schematic_for(cell_name)

    # -- connectivity (Phase 4b) ---------------------------------------

    def run_connectivity_check(self):
        cell = getattr(self, "_current_cell", None)
        if cell is None or not hasattr(cell, "checkConnectivity"):
            self.statusBar().showMessage(
                "no LayoutCell loaded for connectivity check", 3000)
            return
        self.statusBar().showMessage("running connectivity check…")
        try:
            result = cell.checkConnectivity()
        except Exception as exc:
            self.statusBar().showMessage(f"check failed: {exc}", 4000)
            return
        self._connectivity_result = result
        # Determine group filter (active group's nets) if requested
        group_filter = None
        if self.connectivity_panel.filter_to_active_group():
            gs = self._current_groupset
            if gs is not None and gs.any_visible():
                all_inst = cicgroups.collect_top_instance_names(cell)
                nets_for_inst = cicgroups.collect_instance_nets(cell)
                members = gs.visible_members(all_inst, nets_for_inst)
                allowed_nets = set()
                for m in members:
                    allowed_nets.update(nets_for_inst.get(m, set()))
                group_filter = allowed_nets
        # Pre-filter the result if needed (panel placeholder otherwise)
        if group_filter is not None:
            opens = result.get("opens", [])
            filtered_opens = [o for o in opens if o.get("net") in group_filter]
            result_view = dict(result)
            result_view["opens"] = filtered_opens
            self.connectivity_panel.populate(result_view)
        else:
            self.connectivity_panel.populate(result)
        self.statusBar().showMessage(
            f"connectivity check: "
            f"{len(result.get('shorts', []))} shorts, "
            f"{len(result.get('opens', []))} opens",
            5000,
        )

    def _on_connectivity_row(self, payload):
        if not payload:
            return
        t = payload.get("type")
        result = self._connectivity_result or {}
        if t == "short":
            bounds = payload.get("bounds")
            if bounds is not None:
                self.scene.set_short_marker(bounds)
            net_names = payload.get("nets", [])
            # Highlight the first net for context
            if net_names:
                self.schem_scene.highlight_net(net_names[0])
            return
        if t == "unmatched":
            net = payload.get("net")
            anchors = result.get("unmatched", {}).get(net, [])
            segments = self._segments_chain(anchors)
            self.scene.set_flight_lines(segments, color="#FFD000")
            self.schem_scene.highlight_net(net)
            return
        if t == "split":
            net = payload.get("net")
            comp_ids = payload.get("components", [])
            cb = result.get("components_bbox", {})
            anchors = [cb[c] for c in comp_ids if c in cb]
            segments = self._segments_chain(anchors)
            self.scene.set_flight_lines(segments, color="#FFA050")
            self.schem_scene.highlight_net(net)
            return

    def _plan_route_dialog(self, payload):
        """Open a small dialog to author a route entry for the selected open
        net; appends the entry to the chosen planning group's ``routes`` list
        and saves the YAML."""
        from PySide6.QtWidgets import (
            QComboBox, QDialog, QDialogButtonBox,
            QFormLayout, QLineEdit, QMessageBox,
        )
        gs = self._current_groupset
        if gs is None or not gs.groups:
            QMessageBox.information(
                self, "Plan route",
                "Create at least one planning group first.")
            return
        net = payload.get("net", "")
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Plan route — {net}")
        form = QFormLayout(dlg)

        cb_group = QComboBox()
        for g in gs.groups:
            cb_group.addItem(g.name)
        # Default to the panel's selected group
        sel = self.groups_panel.selected_group_name()
        if sel:
            i = cb_group.findText(sel)
            if i >= 0:
                cb_group.setCurrentIndex(i)

        cb_kind = QComboBox()
        cb_kind.addItems(["connection", "orthogonal"])

        ed_layer = QLineEdit("M3")
        ed_layer.setToolTip("connection: target layer; orthogonal: ignored "
                            "(use layer1 / layer2)")
        ed_layer1 = QLineEdit("M2")
        ed_layer2 = QLineEdit("M3")
        ed_options = QLineEdit("")
        ed_options.setPlaceholderText("e.g. onTopLeft,track-2 or top")
        ed_access = QLineEdit("")
        ed_access.setPlaceholderText("orthogonal access layer (optional)")
        ed_parent = QLineEdit("")
        ed_parent.setPlaceholderText("CellGroup name (orthogonal only; blank = layout)")
        ed_location = QLineEdit("")
        ed_location.setPlaceholderText("connection: top|bottom|left|right")

        form.addRow("Planning group:", cb_group)
        form.addRow("Kind:", cb_kind)
        form.addRow("Layer (connection):", ed_layer)
        form.addRow("Layer1 (orthogonal):", ed_layer1)
        form.addRow("Layer2 (orthogonal):", ed_layer2)
        form.addRow("Options:", ed_options)
        form.addRow("Access layer:", ed_access)
        form.addRow("Parent CellGroup:", ed_parent)
        form.addRow("Location (connection):", ed_location)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)

        if dlg.exec() != QDialog.Accepted:
            return

        target_group = gs.by_name(cb_group.currentText())
        if target_group is None:
            return
        kind = cb_kind.currentText()
        entry = {"kind": kind, "net": net}
        if kind == "connection":
            entry["layer"] = ed_layer.text().strip() or "M1"
            if ed_location.text().strip():
                entry["location"] = ed_location.text().strip()
        else:
            entry["layer1"] = ed_layer1.text().strip() or "M2"
            entry["layer2"] = ed_layer2.text().strip() or "M3"
            if ed_access.text().strip():
                entry["access_layer"] = ed_access.text().strip()
            if ed_parent.text().strip():
                entry["parent"] = ed_parent.text().strip()
        if ed_options.text().strip():
            entry["options"] = ed_options.text().strip()

        target_group.routes = list(target_group.routes or []) + [entry]
        self._save_groupset_if_dirty()
        self.statusBar().showMessage(
            f"route added to '{target_group.name}': {kind} {net} "
            f"({len(target_group.routes)} total) — Ctrl+R to rerun spi2mag",
            5000,
        )

    def _segments_chain(self, rects):
        if not rects or len(rects) < 2:
            return []
        centers = [(r.centerX(), r.centerY()) for r in rects]
        segs = []
        for a, b in zip(centers, centers[1:]):
            segs.append((a, b))
        return segs

    # -- planning groups (Phase 4a) ------------------------------------

    def _groupset_path_for(self, cell_name):
        cic_dir = os.path.dirname(os.path.abspath(self.cicfile))
        return os.path.join(cic_dir, f"{cell_name}.groups.yaml")

    def _load_groupset_for(self, cell_name, cell):
        path = self._groupset_path_for(cell_name)
        gs = cicgroups.load_or_empty(path, cell_name)
        self._current_cell = cell
        self._current_groupset = gs
        self.groups_panel.set_groupset(gs)

    def _save_groupset_if_dirty(self):
        gs = self._current_groupset
        if gs is None:
            return
        # Save unconditionally — changes are lightweight YAML; cheap to write.
        if gs.path is None:
            gs.path = self._groupset_path_for(gs.cell)
        try:
            gs.to_yaml()
        except Exception as exc:
            self.statusBar().showMessage(f"groupset save failed: {exc}", 4000)

    def _apply_group_filter(self):
        gs = self._current_groupset
        cell = getattr(self, "_current_cell", None)
        if gs is None or cell is None or not gs.any_visible():
            self.scene.set_member_filter(None)
            self.schem_scene.set_member_filter(None)
            return
        all_inst = cicgroups.collect_top_instance_names(cell)
        nets_for_inst = cicgroups.collect_instance_nets(cell)
        members = gs.visible_members(all_inst, nets_for_inst)
        self.scene.set_member_filter(members)
        self.schem_scene.set_member_filter(members)
        self.statusBar().showMessage(
            f"group filter: {len(members)} member{'s' if len(members) != 1 else ''}",
            3000,
        )

    def _on_groups_changed(self):
        self._save_groupset_if_dirty()
        self._apply_group_filter()

    def _on_add_selection_to_group(self, group_name):
        """Add the currently selected schematic component (and its peers under
        the same naming-convention group) to the named planning group."""
        gs = self._current_groupset
        if gs is None:
            return
        g = gs.by_name(group_name)
        if g is None:
            return
        comp = self._last_clicked_comp
        if comp is None:
            self.statusBar().showMessage(
                "click a schematic component first", 3000)
            return
        peers = list(self.schem_scene.highlight_group_by_prefix(comp.group())) \
            if comp.group() else [comp.name()]
        # Fall back to the single clicked name if no peers.
        if not peers and comp.name():
            peers = [comp.name()]
        added = 0
        for n in peers:
            if n and n not in g.members:
                g.members.append(n)
                added += 1
        self.statusBar().showMessage(
            f"added {added} to '{group_name}' (now {len(g.members)})", 3000)
        self.groups_panel.set_groupset(gs)  # refresh tooltips
        self._on_groups_changed()

    # -- hierarchy navigation ------------------------------------------

    def _descend(self):
        comp = self._last_clicked_comp
        if comp is None:
            self.statusBar().showMessage(
                "press 'e' after clicking a schematic component to descend", 3000)
            return
        sym = comp.symbol or ""
        if not sym:
            return
        cell_name = os.path.splitext(os.path.basename(sym))[0]
        if cell_name not in self.design.cells:
            self.statusBar().showMessage(
                f"no cell named '{cell_name}' in design", 3000)
            return
        current_row = self.cell_list.currentRow()
        current_name = (
            self.cell_list.item(current_row).text() if current_row >= 0 else None
        )
        if current_name == cell_name:
            return
        if current_name:
            self._cell_history.append(current_name)
        row = self.design.cellnames.index(cell_name)
        self.cell_list.setCurrentRow(row)
        self._last_clicked_comp = None

    def _ascend(self):
        if not self._cell_history:
            self.statusBar().showMessage("hierarchy stack is empty", 2000)
            return
        name = self._cell_history.pop()
        if name in self.design.cells:
            row = self.design.cellnames.index(name)
            self.cell_list.setCurrentRow(row)

    # -- schematic discovery -------------------------------------------

    def _build_sch_search_paths(self):
        """Directories to scan for matching <CELL>.sch files."""
        paths = []
        cic_dir = os.path.dirname(os.path.abspath(self.cicfile))
        paths.append(cic_dir)

        # Walk up to the IP root (dir with config.yaml) and from its parent
        # (workspace root), include each <dep>/design/ tree.
        d = cic_dir
        ip_root = None
        for _ in range(8):
            if os.path.isfile(os.path.join(d, "config.yaml")):
                ip_root = d
                break
            new_d = os.path.dirname(d)
            if new_d == d:
                break
            d = new_d
        if ip_root:
            workspace = os.path.dirname(ip_root)
            for entry in sorted(os.listdir(workspace)):
                dep_design = os.path.join(workspace, entry, "design")
                if os.path.isdir(dep_design):
                    paths.append(dep_design)
        # Dedup, preserve order
        seen = set()
        out = []
        for p in paths:
            ap = os.path.abspath(p)
            if ap in seen:
                continue
            seen.add(ap)
            out.append(ap)
        return out

    def _find_sch(self, cell_name):
        if not cell_name:
            return None
        for d in self._sch_search_paths:
            # First try a sibling match (cheap)
            cand = os.path.join(d, cell_name + ".sch")
            if os.path.isfile(cand):
                return cand
            # Then try a recursive match (one level deep)
            for hit in glob.glob(os.path.join(d, "**", cell_name + ".sch"), recursive=True):
                return hit
        return None

    def _load_schematic_for(self, cell_name):
        sch_path = self._find_sch(cell_name)
        self._current_sch_path = None
        if sch_path is None:
            self.schem_scene.set_schematic(None)
            self.schem_view.setVisible(False)
            self.statusBar().showMessage(f"no .sch found for '{cell_name}'", 3000)
            return
        try:
            sch = Schematic.fromFile(sch_path)
        except Exception as exc:
            self.statusBar().showMessage(f"schematic parse failed: {exc}", 4000)
            self.schem_scene.set_schematic(None)
            self.schem_view.setVisible(False)
            return
        self.schem_scene.set_schematic(sch)
        self._current_sch_path = sch_path
        self.schem_view.setVisible(True)
        # If the splitter has collapsed the schem pane (e.g. saved state),
        # nudge sizes so it actually appears.
        sizes = self.splitter.sizes()
        if len(sizes) == 3 and sizes[2] < 50:
            total = sum(sizes) or self.width()
            new = [220, max(300, (total - 220) // 2), max(300, (total - 220) // 2)]
            self.splitter.setSizes(new)
        self.schem_view.fit()
        self.statusBar().showMessage(f"loaded {os.path.basename(sch_path)}", 3000)

    # -- actions --------------------------------------------------------

    def toggle_all_layers(self):
        # If anything visible -> hide all; else show all
        any_visible = any(self.style.is_visible(n) for n in self.style.layer_names())
        target = not any_visible
        for n in self.style.layer_names():
            self.style.set_visible(n, target)
            self.settings.setValue(f"layers/{self.tech_key}/{n}", target)
        self.layer_list.blockSignals(True)
        for i in range(self.layer_list.count()):
            it = self.layer_list.item(i)
            it.setCheckState(Qt.Checked if target else Qt.Unchecked)
        self.layer_list.blockSignals(False)
        self.scene.apply_visibility()

    def reload(self):
        current_row = self.cell_list.currentRow()
        current_name = (
            self.cell_list.item(current_row).text()
            if current_row >= 0 else None
        )
        try:
            self.design = self._load_design()
        except Exception as exc:
            self.statusBar().showMessage(f"reload failed: {exc}")
            return
        self.scene.design = self.design
        self._populate_cells()
        if current_name and current_name in self.design.cells:
            row = self.design.cellnames.index(current_name)
            self.cell_list.setCurrentRow(row)
        elif self.cell_list.count():
            self.cell_list.setCurrentRow(0)
        self._watch_files()
        self.statusBar().showMessage(f"reloaded {os.path.basename(self.cicfile)}", 2000)

    # -- watcher / state -----------------------------------------------

    def _watch_files(self):
        files = self.watcher.files()
        if files:
            self.watcher.removePaths(files)
        if os.path.exists(self.cicfile):
            self.watcher.addPath(self.cicfile)

    def _restore_layer_visibility(self):
        for name, layer in self.rules.layers.items():
            key = f"layers/{self.tech_key}/{name}"
            v = self.settings.value(key, None)
            if v is None:
                continue
            if isinstance(v, str):
                v = v.lower() in ("1", "true", "yes")
            self.style.set_visible(name, bool(v))

    def _restore_window_state(self):
        geom = self.settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(1500, 900)
        splitter = self.settings.value("splitter")
        applied = False
        if splitter is not None:
            applied = self.splitter.restoreState(splitter)
        sizes = self.splitter.sizes()
        # If the saved state predates the schem pane, the third slot may be
        # 0px — fall back to a sensible default.
        if (not applied) or len(sizes) != 3 or any(s < 50 for s in sizes):
            self.splitter.setSizes([220, 700, 700])

    def closeEvent(self, event):
        self._save_groupset_if_dirty()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter", self.splitter.saveState())
        super().closeEvent(event)
