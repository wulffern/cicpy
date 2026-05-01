######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
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


class LayoutScene(QGraphicsScene):

    def __init__(self, design, style, parent=None):
        super().__init__(parent)
        self.design = design
        self.style = style
        self._items_by_layer = {}
        self.cell = None
        self.setBackgroundBrush(QBrush(QColor(20, 20, 20)))

    def set_cell(self, cell):
        self.clear()
        self._items_by_layer.clear()
        self.cell = cell
        if cell is None:
            self.setSceneRect(QRectF())
            return
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
            visible = self.style.is_visible(layer)
            for it in items:
                it.setVisible(visible)

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

    def _walk(self, children, parent):
        for child in children:
            if child is None:
                continue
            if child.isInstance() or child.isCut():
                self._add_instance(child, parent)
            elif child.isPort():
                if getattr(child, "spicePort", False):
                    self._add_port(child, parent)
            elif child.isText():
                # Text rendering is disabled in cic-gui; skip in v1.
                continue
            elif child.isLayoutCell() or child.isCell():
                self._walk(child.children, parent)
            elif child.isRect():
                self._add_rect(child, parent)
            else:
                if hasattr(child, "children"):
                    self._walk(child.children, parent)

    def _add_instance(self, inst, parent):
        cell = self._resolve_inst_cell(inst)
        if cell is None:
            return
        group = QGraphicsItemGroup(parent) if parent else QGraphicsItemGroup()
        p = inst.getCellPoint()
        group.setPos(p.x, p.y)
        group.setTransform(self._instance_transform(inst))
        group.setData(KIND_KEY, "instance")
        group.setData(LAYER_KEY, "_instance")
        self._walk(cell.children, parent=group)
        if parent is None:
            self.addItem(group)

    def _add_rect(self, r, parent):
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
        item.setData(LAYER_KEY, layer)
        item.setData(KIND_KEY, "rect")
        item.setVisible(self.style.is_visible(layer))
        self._items_by_layer.setdefault(layer, []).append(item)
        if parent is None:
            self.addItem(item)

    def _add_port(self, p, parent):
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
        rect_item.setData(LAYER_KEY, layer)
        rect_item.setData(KIND_KEY, "port")
        rect_item.setVisible(self.style.is_visible(layer))
        self._items_by_layer.setdefault(layer, []).append(rect_item)
        if parent is None:
            self.addItem(rect_item)
        # Label
        text_item = QGraphicsSimpleTextItem(p.name, parent=rect_item)
        color = self.style.color(layer)
        if color is not None:
            text_item.setBrush(QBrush(color))
        font = QFont()
        font.setPointSizeF(max(4.0, min(w, h) * 0.3))
        text_item.setFont(font)
        text_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        # Counter the view's Y-flip so text reads upright.
        text_item.setTransform(QTransform().scale(1, -1))
        tbb = text_item.boundingRect()
        text_item.setPos(x1 + w / 2 - tbb.width() / 2,
                         y1 + h / 2 + tbb.height() / 2)
