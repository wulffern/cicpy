######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import os

from PySide6.QtCore import QFileSystemWatcher, QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import cicpy as cic
from .layout_scene import LayoutScene
from .layout_view import LayoutView
from .style import LayerStyle


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

    def __init__(self, cicfile, techfile, includes=()):
        super().__init__()
        self.cicfile = os.path.abspath(cicfile)
        self.techfile = os.path.abspath(techfile) if techfile else None
        self.includes = list(includes or [])
        self.tech_key = _tech_name(self.techfile)

        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.rules = cic.Rules(self.techfile) if self.techfile else cic.Rules()
        self.style = LayerStyle(self.rules)
        self._restore_layer_visibility()

        self.design = self._load_design()

        self.scene = LayoutScene(self.design, self.style)
        self.view = LayoutView(self.scene)

        self.cell_list = QListWidget()
        self.layer_list = QListWidget()
        self.route_list = QListWidget()
        self._populate_cells()
        self._populate_layers()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.addWidget(self.cell_list, 1)
        left_layout.addWidget(self.layer_list, 1)
        left_layout.addWidget(self.route_list, 1)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left)
        self.splitter.addWidget(self.view)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        self.setStatusBar(QStatusBar())

        self.setWindowTitle(
            f"cicpy gui — {os.path.basename(self.cicfile)} "
            f"[{self.tech_key}] (F=fit, Z=zoom-in, Ctrl+Z=zoom-out, right-drag=zoom-area, "
            f"Shift+R reload, T toggle layers)"
        )

        self.cell_list.currentRowChanged.connect(self._on_cell_changed)
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)
        self.route_list.itemChanged.connect(self._on_route_item_changed)
        self.view.cursorMoved.connect(self._on_cursor_moved)

        QShortcut(QKeySequence("Shift+R"), self, activated=self.reload)
        QShortcut(QKeySequence("T"), self, activated=self.toggle_all_layers)

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
        self.scene.set_cell(cell)
        self._populate_routes()
        self.scene.apply_visibility()
        self.view.fit()
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
        # Coordinates are in technology units (Ångström). 10 Å = 1 nm.
        self.statusBar().showMessage(f"x={x:.0f} y={y:.0f}  ({x/10000:.3f},{y/10000:.3f}) µm")

    def _on_file_changed(self, path):
        self._reload_timer.start()

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
            self.resize(1200, 800)
        splitter = self.settings.value("splitter")
        if splitter is not None:
            self.splitter.restoreState(splitter)
        else:
            self.splitter.setSizes([220, 980])

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter", self.splitter.saveState())
        super().closeEvent(event)
