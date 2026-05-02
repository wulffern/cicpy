######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import os

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)


# XSchem default color palette (dark-theme leaning). Refine if needed.
_XSCHEM_COLORS = [
    QColor("#000000"),  # 0 background
    QColor("#3030C0"),  # 1
    QColor("#FFFF80"),  # 2 text labels
    QColor("#E04040"),  # 3 nets / bus
    QColor("#00CC66"),  # 4 wires / device body
    QColor("#FF8080"),  # 5 pins
    QColor("#80E0E0"),  # 6 selection / cursor
    QColor("#A0A0A0"),  # 7
    QColor("#FFFFFF"),  # 8
    QColor("#FFA050"),  # 9
]
_TEXT_COLOR = QColor("#F0F0C0")
_WIRE_PEN_W = 2  # cosmetic; widened slightly for readability


def _color_for(n):
    try:
        n = int(n)
    except Exception:
        return QColor("#A0A0A0")
    if 0 <= n < len(_XSCHEM_COLORS):
        return _XSCHEM_COLORS[n]
    return QColor("#A0A0A0")


def _expand_text(raw, parent_component):
    if parent_component is None or "@" not in raw:
        return raw
    name = parent_component.name() or ""
    sym = parent_component.symbol or ""
    sym_basename = os.path.splitext(os.path.basename(sym))[0]
    out = raw
    out = out.replace("@symname", sym_basename)
    out = out.replace("@name", name)
    return out


class SchemScene(QGraphicsScene):

    componentClicked = Signal(object)  # emits the Component object

    def __init__(self, sym_loader, parent=None):
        super().__init__(parent)
        self.sym_loader = sym_loader
        self.schematic = None
        self._components_by_name = {}
        self._highlight_groups = []
        self._highlight_pen = QPen(QColor("#FFD000"), 0)
        self._highlight_pen.setCosmetic(True)
        self._highlight_pen.setWidth(3)
        self._member_filter = None  # None = no filter; otherwise allowed names
        self._dim_opacity = 0.18
        self.setBackgroundBrush(QBrush(QColor(20, 20, 20)))

    def set_schematic(self, sch):
        self.clear()
        self.schematic = sch
        self._components_by_name.clear()
        self._highlight_groups = []
        self._member_filter = None
        if sch is None:
            self.setSceneRect(QRectF())
            return
        self._render(sch.children, parent=None, parent_component=None)
        bb = self.itemsBoundingRect()
        if not bb.isEmpty():
            mx = bb.width() * 0.05
            my = bb.height() * 0.05
            self.setSceneRect(bb.adjusted(-mx, -my, mx, my))

    def _render(self, children, parent, parent_component):
        for c in children:
            cn = c.__class__.__name__
            if cn == "Wire":
                self._add_wire(c, parent)
            elif cn == "Line":
                self._add_line(c, parent)
            elif cn == "Rect":
                self._add_rect(c, parent)
            elif cn == "Polygon":
                self._add_polygon(c, parent)
            elif cn == "Arc":
                self._add_arc(c, parent)
            elif cn == "Text":
                self._add_text(c, parent, parent_component)
            elif cn == "Component":
                self._add_component(c, parent)

    def _pen(self, color_index, width=0):
        pen = QPen(_color_for(color_index), width)
        pen.setCosmetic(True)
        return pen

    def _add_wire(self, w, parent):
        item = QGraphicsLineItem(w.x1, w.y1, w.x2, w.y2, parent)
        pen = QPen(QColor("#4080FF"), _WIRE_PEN_W)
        pen.setCosmetic(True)
        item.setPen(pen)
        if parent is None:
            self.addItem(item)

    def _add_line(self, l, parent):
        item = QGraphicsLineItem(l.x1, l.y1, l.x2, l.y2, parent)
        item.setPen(self._pen(l.color))
        if parent is None:
            self.addItem(item)

    def _add_rect(self, r, parent):
        item = QGraphicsRectItem(r.x1, r.y1, r.x2 - r.x1, r.y2 - r.y1, parent)
        item.setPen(self._pen(r.color))
        item.setBrush(QBrush(Qt.NoBrush))
        if parent is None:
            self.addItem(item)

    def _add_polygon(self, p, parent):
        poly = QPolygonF([QPointF(x, y) for (x, y) in p.points])
        item = QGraphicsPolygonItem(poly, parent)
        item.setPen(self._pen(p.color))
        item.setBrush(QBrush(Qt.NoBrush))
        if parent is None:
            self.addItem(item)

    def _add_arc(self, a, parent):
        item = QGraphicsEllipseItem(a.x - a.r, a.y - a.r, 2 * a.r, 2 * a.r, parent)
        item.setPen(self._pen(a.color))
        item.setBrush(QBrush(Qt.NoBrush))
        item.setStartAngle(int(a.start_angle * 16))
        item.setSpanAngle(int(a.sweep_angle * 16))
        if parent is None:
            self.addItem(item)

    def _add_text(self, t, parent, parent_component):
        text = _expand_text(t.text, parent_component)
        if not text.strip():
            return
        item = QGraphicsSimpleTextItem(text, parent)
        font = QFont()
        size = max(2.0, float(t.xscale) * 16.0)
        font.setPointSizeF(size)
        item.setFont(font)
        item.setBrush(QBrush(_TEXT_COLOR))
        tr = QTransform()
        if t.flip == 1:
            tr.scale(-1, 1)
        if t.rotation:
            tr.rotate(90 * t.rotation)
        item.setTransform(tr)
        item.setPos(t.x, t.y)
        if parent is None:
            self.addItem(item)

    def _add_component(self, c, parent):
        sym = self.sym_loader.load(c.symbol)
        if sym is None:
            return
        group = QGraphicsItemGroup(parent)
        name = c.name() or ""
        group.setData(0, name)
        group.setData(1, c)
        if name:
            self._components_by_name[name] = group
        try:
            x = float(c.x); y = float(c.y)
        except Exception:
            x = y = 0.0
        try:
            rot = int(c.rotation)
        except Exception:
            rot = 0
        try:
            flp = int(c.flip)
        except Exception:
            flp = 0
        group.setPos(x, y)
        tr = QTransform()
        if flp == 1:
            tr.scale(-1, 1)
        if rot:
            tr.rotate(90 * rot)
        group.setTransform(tr)
        self._render(sym.children, parent=group, parent_component=c)
        # Invisible hit-test rect spanning the symbol bbox so clicks anywhere
        # inside register, not just on the (thin) outline strokes.
        bb = group.childrenBoundingRect()
        if not bb.isEmpty():
            hit = QGraphicsRectItem(bb.adjusted(-2, -2, 2, 2), group)
            hit.setPen(QPen(Qt.NoPen))
            hit.setBrush(QBrush(QColor(0, 0, 0, 1)))
            hit.setZValue(-100)
            hit.setData(0, name)
            hit.setData(1, c)
        if parent is None:
            self.addItem(group)

    # -- selection / highlight ----------------------------------------

    def clear_highlight(self):
        for grp in self._highlight_groups:
            self._restore_pens(grp)
        self._highlight_groups = []

    def highlight_group_by_prefix(self, group_prefix):
        """Highlight all components whose Component.group() == group_prefix."""
        self.clear_highlight()
        if not group_prefix:
            return []
        members = []
        for name, grp in self._components_by_name.items():
            comp = grp.data(1)
            if comp is None:
                continue
            if comp.group() == group_prefix:
                members.append(name)
                self._apply_highlight(grp)
                self._highlight_groups.append(grp)
        return members

    def _apply_highlight(self, group_item):
        for child in group_item.childItems():
            if hasattr(child, "pen"):
                child.setData(2, child.pen())
                child.setPen(self._highlight_pen)

    def _restore_pens(self, group_item):
        for child in group_item.childItems():
            old = child.data(2) if hasattr(child, "data") else None
            if old is not None and hasattr(child, "setPen"):
                child.setPen(old)
                child.setData(2, None)

    # -- planning-group filter ----------------------------------------

    def set_member_filter(self, allowed_names):
        """Dim non-members to ``self._dim_opacity``; full opacity for members.
        Pass None to clear the filter (full opacity for everything)."""
        if allowed_names is None:
            self._member_filter = None
        else:
            self._member_filter = set(allowed_names)
        self._apply_member_filter()

    def _apply_member_filter(self):
        if self._member_filter is None:
            for grp in self._components_by_name.values():
                grp.setOpacity(1.0)
            return
        allowed = self._member_filter
        for name, grp in self._components_by_name.items():
            grp.setOpacity(1.0 if name in allowed else self._dim_opacity)

    # -- mouse --------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            it = self.itemAt(event.scenePos(), QTransform())
            comp = self._component_for_item(it)
            if comp is not None:
                self.componentClicked.emit(comp)
                event.accept()
                return
        super().mousePressEvent(event)

    def _component_for_item(self, item):
        # walk up parent chain looking for our component-tagged group
        while item is not None:
            comp = item.data(1)
            if comp is not None and item.data(0):
                return comp
            item = item.parentItem()
        return None
