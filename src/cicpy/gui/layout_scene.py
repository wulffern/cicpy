######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from cicpy.core.layer import Material


# Material types that are not useful in a layout viewer; hard-skipped to keep
# the scene small. Matches the SvgPrinter skip rule.
SKIP_MATERIAL_NAMES = {"metalres", "marker", "implant"}

LAYER_KEY = 0
KIND_KEY = 1
ROUTE_KEY = 2
INSTANCE_NAME_KEY = 4
ROUTE_CLASSES = {
    "Route",
    "OrthogonalLayerRoute",
    "cIcCore::Route",
    "cIcCore::OrthogonalLayerRoute",
}
TEXT_FONT_SIZE = 18.0
TEXT_Z_VALUE = 1000


class LayoutScene(QGraphicsScene):

    instanceClicked = Signal(str)

    def __init__(self, design, style, parent=None):
        super().__init__(parent)
        # Optional set of allowed top-level instance names; None disables
        # filtering. Empty set hides everything.
        self._member_filter = None
        self.design = design
        self.style = style
        self._items_by_layer = {}
        self._items_by_route = {}
        self._route_visible = {}
        self._route_labels = {}
        self._route_order = []
        self._port_label_names = set()
        self._groups_by_instance = {}
        self._highlight_overlays = []
        self.cell = None
        self.setBackgroundBrush(QBrush(QColor(20, 20, 20)))

    def set_cell(self, cell):
        self.clear()
        self._items_by_layer.clear()
        self._items_by_route.clear()
        self._route_visible.clear()
        self._route_labels.clear()
        self._route_order.clear()
        self._port_label_names.clear()
        self._groups_by_instance.clear()
        self._highlight_overlays = []
        self._flight_items = []
        self._member_filter = None
        self.cell = cell
        if cell is None:
            self.setSceneRect(QRectF())
            return
        self._port_label_names = self._collect_top_port_label_names(cell.children)
        self._walk(cell.children, parent=None)
        bb = cell.calcBoundingRect()
        if bb is not None and bb.width() > 0 and bb.height() > 0:
            margin_x = bb.width() * 0.05
            margin_y = bb.height() * 0.05
            self.setSceneRect(QRectF(
                bb.x1 - margin_x,
                bb.y1 - margin_y,
                bb.width() + 2 * margin_x,
                bb.height() + 2 * margin_y,
            ))
        else:
            self.setSceneRect(self.itemsBoundingRect())

    def apply_visibility(self):
        for layer, items in self._items_by_layer.items():
            for it in items:
                route_key = it.data(ROUTE_KEY)
                route_visible = (
                    True if route_key is None else self.is_route_visible(route_key)
                )
                layer_visible = self.style.is_visible(layer)
                it.setVisible(layer_visible and route_visible)

    def route_names(self):
        return list(self._route_order)

    def route_label(self, key):
        return self._route_labels.get(key, key)

    def _route_base_name(self, key):
        return self._route_labels.get(key, key).split(" (", 1)[0]

    def connected_route_names(self):
        connected = set()
        items_by_layer = {}
        for route_key, items in self._items_by_route.items():
            for item in items:
                layer = item.data(LAYER_KEY)
                if not layer:
                    continue
                items_by_layer.setdefault(layer, []).append((route_key, item))

        for items in items_by_layer.values():
            for i, (route_a, item_a) in enumerate(items):
                rect_a = item_a.sceneBoundingRect().adjusted(-0.1, -0.1, 0.1, 0.1)
                for route_b, item_b in items[i + 1:]:
                    if route_a == route_b:
                        continue
                    if self._route_base_name(route_a) == self._route_base_name(route_b):
                        continue
                    if rect_a.intersects(item_b.sceneBoundingRect()):
                        connected.add(route_a)
                        connected.add(route_b)
        return connected

    def is_route_visible(self, key):
        return self._route_visible.get(key, True)

    def set_route_visible(self, key, visible):
        if key in self._items_by_route:
            self._route_visible[key] = bool(visible)

    def _is_route(self, obj):
        return getattr(obj, "classname", obj.__class__.__name__) in ROUTE_CLASSES

    def _route_key(self, route):
        base = getattr(route, "name", "") or getattr(route, "net", "") or "route"
        route_class = getattr(route, "classname", route.__class__.__name__)
        label = f"{base} ({route_class})"
        key = label
        suffix = 2
        while key in self._route_labels:
            key = f"{label} #{suffix}"
            suffix += 1
        self._route_labels[key] = label if key == label else key
        self._route_visible[key] = True
        self._route_order.append(key)
        return key

    def _resolve_inst_cell(self, inst):
        cell_obj = getattr(inst, "_cell_obj", None)
        if cell_obj is not None:
            return cell_obj
        if getattr(inst, "layoutcell", None) is not None:
            return inst.layoutcell
        name = getattr(inst, "cell", "")
        if name and self.design is not None and name in self.design.cells:
            return self.design.cells[name]
        return None

    def _instance_transform(self, inst):
        t = QTransform()
        a = inst.angle or ""
        if a == "R90":
            t.rotate(90)
        elif a == "R180":
            t.rotate(180)
        elif a == "R270":
            t.rotate(270)
        elif a == "MX":
            t.scale(1, -1)
        elif a == "MY":
            t.scale(-1, 1)
        return t

    def _collect_top_port_label_names(self, children):
        names = set()
        for child in children:
            if child is None:
                continue
            if child.isPort():
                if getattr(child, "spicePort", False) and getattr(child, "name", ""):
                    names.add(child.name)
        return names

    def _walk(self, children, parent, route_key=None, show_port_labels=True):
        for child in children:
            if child is None:
                continue
            child_route_key = route_key
            if self._is_route(child):
                child_route_key = self._route_key(child)
            if child.isInstance() or child.isCut():
                self._add_instance(child, parent, child_route_key)
            elif child.isPort():
                if getattr(child, "spicePort", False):
                    self._add_port(child, parent, child_route_key, show_port_labels)
            elif child.isText():
                self._add_text(child, parent, child_route_key)
            elif child.isLayoutCell() or child.isCell():
                self._walk(child.children, parent, child_route_key, show_port_labels)
            elif child.isRect():
                self._add_rect(child, parent, child_route_key)
            else:
                if hasattr(child, "children"):
                    self._walk(child.children, parent, child_route_key, show_port_labels)

    def _add_instance(self, inst, parent, route_key=None):
        cell = self._resolve_inst_cell(inst)
        if cell is None:
            return
        group = QGraphicsItemGroup(parent) if parent else QGraphicsItemGroup()
        p = inst.getCellPoint()
        group.setPos(p.x, p.y)
        group.setTransform(self._instance_transform(inst))
        group.setData(KIND_KEY, "instance")
        group.setData(LAYER_KEY, "_instance")
        # Tag top-level instances by their SPICE instanceName for cross-probing.
        # Nested instances (parent != None) aren't indexed — they're physical
        # primitives below the user-meaningful hierarchy boundary.
        inst_name = getattr(inst, "instanceName", "") or ""
        if parent is None and inst_name:
            group.setData(INSTANCE_NAME_KEY, inst_name)
            self._groups_by_instance[inst_name] = group
        self._walk(cell.children, parent=group, route_key=route_key, show_port_labels=False)
        # Invisible hit-test rect over the whole instance bbox so clicks in
        # gaps between rendered rects still register.
        if parent is None and inst_name:
            bb = group.childrenBoundingRect()
            if not bb.isEmpty():
                hit = QGraphicsRectItem(bb, group)
                hit.setPen(QPen(Qt.NoPen))
                hit.setBrush(QBrush(QColor(0, 0, 0, 1)))
                hit.setZValue(-1000)
                hit.setData(INSTANCE_NAME_KEY, inst_name)
        if parent is None:
            self.addItem(group)

    def _register_item(self, item, layer, route_key, include_in_route=True):
        item.setData(LAYER_KEY, layer)
        item.setData(ROUTE_KEY, route_key)
        self._items_by_layer.setdefault(layer, []).append(item)
        if include_in_route and route_key is not None:
            self._items_by_route.setdefault(route_key, []).append(item)

    def _item_visible(self, layer, route_key, kind):
        layer_visible = self.style.is_visible(layer)
        route_visible = route_key is None or self.is_route_visible(route_key)
        return layer_visible and route_visible

    def _make_text_item(self, name, x, y, layer, parent, route_key, font_size=8.0):
        if not name:
            return None
        item = QGraphicsSimpleTextItem(name, parent=parent)
        item.setBrush(QBrush(QColor(255, 255, 255)))
        font = QFont()
        font.setPointSizeF(font_size)
        font.setBold(True)
        item.setFont(font)
        item.setFlag(item.GraphicsItemFlag.ItemIgnoresTransformations, True)
        item.setZValue(TEXT_Z_VALUE)
        item.setData(KIND_KEY, "text")
        self._register_item(item, layer, route_key, include_in_route=False)
        item.setPos(x, y)
        item.setVisible(self._item_visible(layer, route_key, "text"))
        if parent is None:
            self.addItem(item)
        return item

    def _add_rect(self, r, parent, route_key=None):
        if r.x1 == r.x2 or r.y1 == r.y2:
            return
        layer = r.layer or ""
        if not layer:
            return
        layer_obj = self.style.rules.getLayer(layer)
        if layer_obj is None:
            return
        material_name = getattr(layer_obj.material, "name", "").lower()
        if material_name in SKIP_MATERIAL_NAMES:
            return
        pen = self.style.pen(layer)
        if pen is None:
            return
        brush = self.style.brush(layer)
        x1, y1 = r.x1, r.y1
        w, h = r.x2 - r.x1, r.y2 - r.y1
        item = QGraphicsRectItem(x1, y1, w, h, parent=parent)
        item.setPen(pen)
        item.setBrush(brush)
        item.setData(KIND_KEY, "rect")
        self._register_item(item, layer, route_key)
        item.setVisible(self._item_visible(layer, route_key, "rect"))
        if parent is None:
            self.addItem(item)

    def _add_port(self, p, parent, route_key=None, show_label=True):
        layer = getattr(p, "pinLayer", None) or p.layer or ""
        if not layer:
            return
        layer_obj = self.style.rules.getLayer(layer)
        if layer_obj is None:
            return
        pen = self.style.pen(layer)
        brush = self.style.brush(layer)
        if pen is None:
            return
        x1, y1 = p.x1, p.y1
        w, h = p.x2 - p.x1, p.y2 - p.y1
        if w == 0 or h == 0:
            return
        rect_item = QGraphicsRectItem(x1, y1, w, h, parent=parent)
        rect_item.setPen(pen)
        rect_item.setBrush(brush)
        rect_item.setData(KIND_KEY, "port")
        self._register_item(rect_item, layer, route_key)
        rect_item.setVisible(self._item_visible(layer, route_key, "port"))
        if parent is None:
            self.addItem(rect_item)
        if not show_label:
            return
        # Label
        text_item = self._make_text_item(
            p.name,
            x1,
            y1,
            "TXT",
            parent,
            route_key,
            TEXT_FONT_SIZE,
        )
        tbb = text_item.boundingRect()
        text_item.setPos(x1 + w / 2 - tbb.width() / 2,
                         y1 + h / 2 + tbb.height() / 2)

    def _add_text(self, t, parent, route_key=None):
        if t.name in self._port_label_names:
            return
        layer = t.layer or "TXT"
        self._make_text_item(t.name, t.x1, t.y1, layer, parent, route_key, TEXT_FONT_SIZE)

    # -- selection / cross-probing -----------------------------------

    def instance_names(self):
        return list(self._groups_by_instance.keys())

    def clear_highlight(self):
        for it in self._highlight_overlays:
            try:
                self.removeItem(it)
            except Exception:
                pass
        self._highlight_overlays = []

    def highlight_instances(self, names):
        """Outline matching top-level instances. Returns the list of names that
        actually matched a tagged instance group."""
        self.clear_highlight()
        matched = []
        pen = QPen(QColor("#FFD000"))
        pen.setCosmetic(True)
        pen.setWidth(3)
        for name in names:
            grp = self._groups_by_instance.get(name)
            if grp is None:
                continue
            matched.append(name)
            bb = grp.sceneBoundingRect().adjusted(-20, -20, 20, 20)
            overlay = self.addRect(bb, pen, QBrush(Qt.NoBrush))
            overlay.setZValue(TEXT_Z_VALUE + 10)
            self._highlight_overlays.append(overlay)
        return matched

    def highlight_instance_prefix(self, prefix):
        """Highlight every instance whose name starts with `prefix`. Useful when
        the schematic component group key is the longest non-digit prefix."""
        if not prefix:
            self.clear_highlight()
            return []
        matches = [n for n in self._groups_by_instance if n.startswith(prefix)]
        return self.highlight_instances(matches)

    def set_member_filter(self, allowed_names):
        """Restrict visible top-level instances to ``allowed_names``. Pass
        None to disable filtering. Empty set hides every tagged instance."""
        if allowed_names is None:
            self._member_filter = None
        else:
            self._member_filter = set(allowed_names)
        self._apply_member_filter()

    def _apply_member_filter(self):
        if self._member_filter is None:
            for grp in self._groups_by_instance.values():
                grp.setVisible(True)
            return
        allowed = self._member_filter
        for name, grp in self._groups_by_instance.items():
            grp.setVisible(name in allowed)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            for it in self.items(event.scenePos()):
                name = self._top_instance_name_for(it)
                if name:
                    self.instanceClicked.emit(name)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def _top_instance_name_for(self, item):
        while item is not None:
            n = item.data(INSTANCE_NAME_KEY)
            if n:
                return n
            item = item.parentItem()
        return None

    # -- flight lines / problem markers (Phase 4b) -------------------

    def clear_flight_lines(self):
        for it in getattr(self, "_flight_items", []):
            try:
                self.removeItem(it)
            except Exception:
                pass
        self._flight_items = []

    def set_flight_lines(self, segments, color="#FFD000", width=4):
        """Draw straight flight lines on top of the layout. ``segments`` is
        a list of ((x1,y1),(x2,y2)) pairs. Replaces any prior flight lines."""
        self.clear_flight_lines()
        if not segments:
            return
        c = QColor(color)
        pen = QPen(c)
        pen.setCosmetic(True)
        pen.setWidth(width)
        pen.setStyle(Qt.DashLine)
        items = []
        for (x1, y1), (x2, y2) in segments:
            line = QGraphicsLineItem(x1, y1, x2, y2)
            line.setPen(pen)
            line.setZValue(TEXT_Z_VALUE + 20)
            self.addItem(line)
            items.append(line)
        self._flight_items = items

    def set_short_marker(self, rect, color="#FF4040"):
        """Highlight the bbox of a short."""
        self.clear_flight_lines()
        c = QColor(color)
        pen = QPen(c)
        pen.setCosmetic(True)
        pen.setWidth(4)
        item = self.addRect(rect.x1, rect.y1, rect.x2 - rect.x1, rect.y2 - rect.y1,
                            pen, QBrush(QColor(c.red(), c.green(), c.blue(), 40)))
        item.setZValue(TEXT_Z_VALUE + 20)
        self._flight_items = [item]

    def fit_highlighted(self, view):
        if not self._highlight_overlays:
            return
        rect = QRectF()
        for it in self._highlight_overlays:
            r = it.sceneBoundingRect()
            if rect.isEmpty():
                rect = QRectF(r)
            else:
                rect = rect.united(r)
        if not rect.isEmpty():
            margin = max(rect.width(), rect.height()) * 0.5
            rect.adjust(-margin, -margin, margin, margin)
            view.fitInView(rect, Qt.KeepAspectRatio)
