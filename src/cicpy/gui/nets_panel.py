######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

"""Nets panel — every ``lab=`` net found in the loaded schematic."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class NetsPanel(QWidget):

    netActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_nets = []
        self._allowed_nets = None  # None = no filter

        self.search = QLineEdit()
        self.search.setPlaceholderText("filter…")
        self.cb_filter = QCheckBox("Active group only")
        self.lbl = QLabel("(no schematic)")
        self.list = QListWidget()

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.search, 1)
        top.addWidget(self.cb_filter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addLayout(top)
        layout.addWidget(self.lbl)
        layout.addWidget(self.list, 1)

        self.search.textChanged.connect(self._refresh)
        self.cb_filter.toggled.connect(self._refresh)
        self.list.itemClicked.connect(self._on_row)

    # public

    def set_nets(self, net_names):
        self._all_nets = sorted(set(net_names or []))
        self._refresh()

    def set_group_filter(self, allowed_nets):
        """``allowed_nets`` is the set of nets reachable from the active
        planning group's members; ``None`` disables the filter."""
        self._allowed_nets = (
            None if allowed_nets is None else set(allowed_nets)
        )
        self._refresh()

    # internal

    def _refresh(self):
        self.list.clear()
        if not self._all_nets:
            self.lbl.setText("(no schematic)")
            return
        needle = self.search.text().strip().lower()
        use_filter = self.cb_filter.isChecked() and self._allowed_nets is not None
        shown = []
        for net in self._all_nets:
            if needle and needle not in net.lower():
                continue
            if use_filter and net not in self._allowed_nets:
                continue
            shown.append(net)
        for net in shown:
            self.list.addItem(QListWidgetItem(net))
        self.lbl.setText(f"{len(shown)} / {len(self._all_nets)} nets")

    def _on_row(self, item):
        if item is not None:
            self.netActivated.emit(item.text())
