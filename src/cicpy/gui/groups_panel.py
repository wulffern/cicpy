######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

"""Planning groups panel — left-pane widget for Phase 4a."""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cicpy.groups import Group, GroupSet


class GroupsPanel(QWidget):
    """Edits a GroupSet for the active cell. Emits ``filterChanged`` whenever
    the set of visible members may have changed (group added/removed/renamed,
    visibility toggled, members edited)."""

    filterChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gs: GroupSet | None = None
        self._suppress_signal = False

        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)

        self.btn_new = QPushButton("New")
        self.btn_add_sel = QPushButton("Add selection")
        self.btn_add_sel.setToolTip(
            "Add the schematic-clicked component (and its peers in the same\n"
            "naming-convention group) to the currently selected planning group."
        )
        self.btn_remove = QPushButton("Remove")
        self.btn_rename = QPushButton("Rename schem")
        self.btn_rename.setToolTip(
            "Rename the currently shift-selected schematic components under a\n"
            "new prefix (writes the .sch in place; .sch.bak saved as backup)."
        )

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_add_sel)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_rename)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addLayout(row)
        layout.addWidget(self.list, 1)

        self.list.itemChanged.connect(self._on_item_changed)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        self.btn_new.clicked.connect(self._on_new)
        self.btn_add_sel.clicked.connect(self._on_add_selection_clicked)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_rename.clicked.connect(self.renameSchemSelectionRequested.emit)

    # callable set by MainWindow when the user clicks "Add selection"
    addSelectionRequested = Signal(str)  # group name
    renameSchemSelectionRequested = Signal()

    # ---- public API ---------------------------------------------------

    def set_groupset(self, gs: GroupSet | None):
        self._gs = gs
        self._populate()

    def groupset(self) -> GroupSet | None:
        return self._gs

    def selected_group_name(self) -> str:
        it = self.list.currentItem()
        return it.text() if it else ""

    def add_members_to_selected(self, names):
        if self._gs is None:
            return
        gname = self.selected_group_name()
        if not gname:
            return
        g = self._gs.by_name(gname)
        if g is None:
            return
        for n in names:
            g.add_member(n)
        self.filterChanged.emit()

    # ---- list population ---------------------------------------------

    def _populate(self):
        self._suppress_signal = True
        self.list.clear()
        if self._gs is not None:
            for g in self._gs.groups:
                item = QListWidgetItem(g.name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if g.visible else Qt.Unchecked)
                tip_lines = []
                if g.description:
                    tip_lines.append(g.description)
                if g.members:
                    tip_lines.append(f"members: {len(g.members)}")
                if g.member_regex:
                    tip_lines.append(f"regex: {', '.join(g.member_regex)}")
                if g.member_nets:
                    tip_lines.append(f"nets: {', '.join(g.member_nets)}")
                item.setToolTip("\n".join(tip_lines))
                self.list.addItem(item)
        self._suppress_signal = False

    # ---- callbacks ----------------------------------------------------

    def _on_item_changed(self, item):
        if self._suppress_signal or self._gs is None:
            return
        g = self._gs.by_name(item.text())
        if g is None:
            return
        new_vis = item.checkState() == Qt.Checked
        if g.visible != new_vis:
            g.visible = new_vis
            self.filterChanged.emit()

    def _on_new(self):
        if self._gs is None:
            QMessageBox.information(self, "Groups", "Open a cell first.")
            return
        name, ok = QInputDialog.getText(self, "New planning group", "Name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if self._gs.by_name(name):
            QMessageBox.warning(self, "Groups", f"Group '{name}' already exists.")
            return
        self._gs.add(Group(name=name, visible=True))
        self._populate()
        # select the new group
        for i in range(self.list.count()):
            if self.list.item(i).text() == name:
                self.list.setCurrentRow(i)
                break
        self.filterChanged.emit()

    def _on_remove(self):
        if self._gs is None:
            return
        name = self.selected_group_name()
        if not name:
            return
        if QMessageBox.question(
            self, "Remove group", f"Remove '{name}'?"
        ) != QMessageBox.Yes:
            return
        self._gs.remove(name)
        self._populate()
        self.filterChanged.emit()

    def _on_add_selection_clicked(self):
        name = self.selected_group_name()
        if not name:
            QMessageBox.information(self, "Groups", "Select a group first.")
            return
        self.addSelectionRequested.emit(name)

    def _on_context_menu(self, pos):
        if self._gs is None:
            return
        item = self.list.itemAt(pos)
        if item is None:
            return
        gname = item.text()
        g = self._gs.by_name(gname)
        if g is None:
            return
        menu = QMenu(self)
        a_rename = menu.addAction("Rename…")
        a_desc = menu.addAction("Edit description…")
        a_regex = menu.addAction("Edit member regex…")
        a_members = menu.addAction("Edit members…")
        a_place = menu.addAction("Edit placement…")
        menu.addSeparator()
        a_remove = menu.addAction("Remove")
        chosen = menu.exec(self.list.mapToGlobal(pos))
        if chosen is a_rename:
            new, ok = QInputDialog.getText(self, "Rename", "Name:", text=g.name)
            if ok and new.strip() and new.strip() != g.name:
                if self._gs.by_name(new.strip()):
                    QMessageBox.warning(self, "Groups", "Name already exists.")
                    return
                g.name = new.strip()
                self._populate()
                self.filterChanged.emit()
        elif chosen is a_desc:
            new, ok = QInputDialog.getMultiLineText(
                self, "Description", "Description:", g.description
            )
            if ok:
                g.description = new
                self._populate()
        elif chosen is a_regex:
            cur = "\n".join(g.member_regex)
            new, ok = QInputDialog.getMultiLineText(
                self, "Member regex (one per line)", "Patterns:", cur
            )
            if ok:
                patterns = [p.strip() for p in new.splitlines() if p.strip()]
                # Validate
                bad = []
                for p in patterns:
                    try:
                        re.compile(p)
                    except re.error as exc:
                        bad.append(f"{p}: {exc}")
                if bad:
                    QMessageBox.warning(self, "Regex error", "\n".join(bad))
                    return
                g.member_regex = patterns
                self._populate()
                self.filterChanged.emit()
        elif chosen is a_members:
            cur = "\n".join(g.members)
            new, ok = QInputDialog.getMultiLineText(
                self, "Members (one per line)", "Instance names:", cur
            )
            if ok:
                g.members = [m.strip() for m in new.splitlines() if m.strip()]
                self._populate()
                self.filterChanged.emit()
        elif chosen is a_place:
            self._edit_placement(g)
        elif chosen is a_remove:
            self._on_remove()

    def _edit_placement(self, g):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Placement — {g.name}")
        form = QFormLayout(dlg)
        cb_stack = QCheckBox("Emit addStack() for this group")
        cb_stack.setChecked(bool(g.placement.get("stack", False)))
        ed_parent = QLineEdit(g.placement.get("parent", "") or "")
        ed_parent.setPlaceholderText("CellGroup name (e.g. nmos)")
        ed_regex = QLineEdit(g.placement.get("instances_regex", "") or "")
        ed_regex.setPlaceholderText("regex on instanceName (overrides members)")
        form.addRow("", cb_stack)
        form.addRow("Parent CellGroup:", ed_parent)
        form.addRow("Instance regex:", ed_regex)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        place = dict(g.placement or {})
        if cb_stack.isChecked():
            place["stack"] = True
        else:
            place.pop("stack", None)
        parent = ed_parent.text().strip()
        if parent:
            place["parent"] = parent
        else:
            place.pop("parent", None)
        regex = ed_regex.text().strip()
        if regex:
            place["instances_regex"] = regex
        else:
            place.pop("instances_regex", None)
        g.placement = place
        self._populate()
        self.filterChanged.emit()  # triggers save
