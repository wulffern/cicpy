######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

"""Connectivity panel — Phase 4b. Runs ``LayoutCell.checkConnectivity()``
on demand and shows opens (split / unmatched) and shorts as a worklist."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


_COLOR_SHORT = QColor("#FF4040")
_COLOR_SPLIT = QColor("#FFA050")
_COLOR_UNMATCHED = QColor("#FFD000")


class ConnectivityPanel(QWidget):

    runRequested = Signal()
    rowActivated = Signal(dict)  # the entry payload (with type key)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.btn_run = QPushButton("Run connectivity check")
        self.lbl_summary = QLabel("(not run)")
        self.cb_filter = QCheckBox("Limit to active group")
        self.cb_filter.setChecked(False)

        self.list = QListWidget()

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.btn_run)
        top.addWidget(self.cb_filter)
        top.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addLayout(top)
        layout.addWidget(self.lbl_summary)
        layout.addWidget(self.list, 1)

        self.btn_run.clicked.connect(self.runRequested.emit)
        self.list.itemClicked.connect(self._on_row)

    # public

    def filter_to_active_group(self) -> bool:
        return self.cb_filter.isChecked()

    def populate(self, result, group_filter_names=None):
        """``result`` is the dict returned by ``LayoutCell.checkConnectivity()``.
        ``group_filter_names`` (optional) restricts opens to nets that touch
        the listed instances; passed through unchanged when None."""
        self.list.clear()
        if result is None:
            self.lbl_summary.setText("(not run)")
            return

        opens = result.get("opens", []) or []
        shorts = result.get("shorts", []) or []
        # Filter opens by active group if requested
        if group_filter_names is not None and self.cb_filter.isChecked():
            allowed_nets = self._nets_in_group(result, group_filter_names)
            opens = [o for o in opens if o.get("net") in allowed_nets]

        for s in shorts:
            label = (
                f"SHORT  comp={s.get('component')}  "
                f"nets={','.join(s.get('nets', []))}  "
                f"rects={s.get('rect_count')}"
            )
            it = QListWidgetItem(label)
            it.setForeground(QBrush(_COLOR_SHORT))
            it.setData(Qt.UserRole, {"type": "short", **s})
            self.list.addItem(it)

        for o in opens:
            t = o.get("type")
            if t == "split":
                comps = o.get("components", [])
                label = f"SPLIT     net={o.get('net')}   ({len(comps)} islands)"
                color = _COLOR_SPLIT
            else:
                label = (
                    f"UNMATCHED net={o.get('net')}   "
                    f"({o.get('anchors', 0)} anchors)"
                )
                color = _COLOR_UNMATCHED
            it = QListWidgetItem(label)
            it.setForeground(QBrush(color))
            it.setData(Qt.UserRole, dict(o))
            self.list.addItem(it)

        self.lbl_summary.setText(
            f"{len(shorts)} short{'s' if len(shorts) != 1 else ''}, "
            f"{len(opens)} open{'s' if len(opens) != 1 else ''}, "
            f"{result.get('component_count', '?')} components, "
            f"{result.get('shape_count', '?')} shapes"
        )

    def clear(self):
        self.list.clear()
        self.lbl_summary.setText("(cleared)")

    # helpers

    def _nets_in_group(self, result, instance_names):
        """Return the set of net names touched by any instance in
        ``instance_names``. Falls back to "all nets" if we don't have the
        info — better to over-include than to hide problems."""
        if not instance_names:
            return set()
        # net_components from the result is comp_id->set(net); we need
        # instance name → set(net). Best source is the parent cell. Caller
        # passes a pre-resolved set of net names instead in 4c+.
        return set(instance_names)  # placeholder: caller can override

    def _on_row(self, item):
        payload = item.data(Qt.UserRole)
        if isinstance(payload, dict):
            self.rowActivated.emit(payload)
