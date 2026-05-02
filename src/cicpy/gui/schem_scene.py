######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import os
import re

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
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


_AT_TOKEN_RE = re.compile(r"@([A-Za-z_]\w*)")


def _expand_text(raw, parent_component):
    """Replace ``@<key>`` tokens in symbol-internal text with the parent
    component's properties. Anything still unresolved is dropped so we
    never render literal @foo on screen."""
    if "@" not in raw:
        return raw
    if parent_component is None:
        return _AT_TOKEN_RE.sub("", raw).strip()
    sym = parent_component.symbol or ""
    sym_basename = os.path.splitext(os.path.basename(sym))[0]
    props = parent_component.properties or {}

    def _sub(m):
        key = m.group(1)
        if key == "symname":
            return sym_basename
        if key == "name":
            v = props.get("name")
            if v is not None:
                return str(v).strip('"')
            return ""
        v = props.get(key)
        if v is None:
            return ""
        return str(v).strip('"')

    out = _AT_TOKEN_RE.sub(_sub, raw)
    # Collapse runs of whitespace left from dropped tokens
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


class SchemScene(QGraphicsScene):

    componentClicked = Signal(object)  # emits the Component object
    selectionChanged = Signal(list)    # list[Component] — multi-selection

    def __init__(self, sym_loader, parent=None):
        super().__init__(parent)
        self.sym_loader = sym_loader
        self.schematic = None
        self._components_by_name = {}
        self._highlight_groups = []
        self._highlight_pen = QPen(QColor("#FFD000"), 0)
        self._highlight_pen.setCosmetic(True)
        self._highlight_pen.setWidth(3)
        self._select_pen = QPen(QColor("#FF40FF"), 0)
        self._select_pen.setCosmetic(True)
        self._select_pen.setWidth(4)
        self._member_filter = None  # None = no filter; otherwise allowed names
        self._dim_opacity = 0.18
        self._wires_by_net = {}      # net_name -> list[QGraphicsLineItem]
        self._net_highlight_items = []
        # Multi-selection (shift-click) — kept in user-click order so rename
        # can assign indices in the order the user picked them.
        self._selected_components = []     # list[Component]
        self._selection_overlays = []      # list[QGraphicsRectItem]
        self.setBackgroundBrush(QBrush(QColor(20, 20, 20)))

    def set_schematic(self, sch):
        self.clear()
        self.schematic = sch
        self._components_by_name.clear()
        self._highlight_groups = []
        self._wires_by_net = {}
        self._net_highlight_items = []
        self._selected_components = []
        self._selection_overlays = []
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
        net = (w.properties or {}).get("lab")
        if net:
            item.setData(3, net)
            item.setToolTip(f"net: {net}")
            item.setAcceptHoverEvents(True)
            self._wires_by_net.setdefault(net, []).append(item)
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
        if not text:
            return
        item = QGraphicsSimpleTextItem(text, parent)
        font = QFont()
        size = max(2.0, float(t.xscale) * 16.0)
        font.setPointSizeF(size)
        item.setFont(font)
        item.setBrush(QBrush(_TEXT_COLOR))
        item.setPos(t.x, t.y)
        # Keep symbol-internal labels upright regardless of the parent
        # component's rotation/flip; ItemIgnoresTransformations also pins the
        # render size so labels stay legible at all zoom levels.
        if parent_component is not None:
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            # Free-floating text in the schematic gets its own rot/flip.
            tr = QTransform()
            if t.flip == 1:
                tr.scale(-1, 1)
            if t.rotation:
                tr.rotate(90 * t.rotation)
            item.setTransform(tr)
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

    # -- net highlight (Phase 4b) -------------------------------------

    def clear_net_highlight(self):
        for it in getattr(self, "_net_highlight_items", []):
            try:
                old = it.data(2)
                if old is not None and hasattr(it, "setPen"):
                    it.setPen(old)
                    it.setData(2, None)
            except Exception:
                pass
        self._net_highlight_items = []

    def highlight_net(self, net_name, color="#FFD000", width=4):
        """Highlight every wire whose ``lab=`` property matches ``net_name``."""
        self.clear_net_highlight()
        if not net_name:
            return 0
        wires = self._wires_by_net.get(net_name, [])
        pen = QPen(QColor(color))
        pen.setCosmetic(True)
        pen.setWidth(width)
        items = []
        for it in wires:
            it.setData(2, it.pen())
            it.setPen(pen)
            items.append(it)
        self._net_highlight_items = items
        return len(items)

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
                if event.modifiers() & Qt.ShiftModifier:
                    self._toggle_in_selection(comp)
                else:
                    self._set_selection([comp])
                self.componentClicked.emit(comp)
                event.accept()
                return
            # Empty space click without modifier → clear selection
            if not (event.modifiers() & Qt.ShiftModifier):
                if self._selected_components:
                    self._set_selection([])
        super().mousePressEvent(event)

    def _component_for_item(self, item):
        # walk up parent chain looking for our component-tagged group
        while item is not None:
            comp = item.data(1)
            if comp is not None and item.data(0):
                return comp
            item = item.parentItem()
        return None

    # -- multi-selection ----------------------------------------------

    def selected_components(self):
        return list(self._selected_components)

    def clear_selection(self):
        self._set_selection([])

    def _toggle_in_selection(self, comp):
        if comp in self._selected_components:
            self._selected_components.remove(comp)
        else:
            self._selected_components.append(comp)
        self._refresh_selection_overlays()
        self.selectionChanged.emit(list(self._selected_components))

    def _set_selection(self, comps):
        self._selected_components = list(comps)
        self._refresh_selection_overlays()
        self.selectionChanged.emit(list(self._selected_components))

    def _refresh_selection_overlays(self):
        for it in self._selection_overlays:
            try:
                self.removeItem(it)
            except Exception:
                pass
        self._selection_overlays = []
        for comp in self._selected_components:
            grp = self._components_by_name.get(comp.name() or "")
            if grp is None:
                continue
            bb = grp.sceneBoundingRect().adjusted(-2, -2, 2, 2)
            overlay = self.addRect(bb, self._select_pen, QBrush(Qt.NoBrush))
            overlay.setZValue(2000)
            self._selection_overlays.append(overlay)
