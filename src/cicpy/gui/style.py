######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtCore import Qt

from cicpy.core.layer import Material


SKIP_MATERIALS = {Material.METALRES, Material.MARKER, Material.IMPLANT}


def _qcolor(rgb_string):
    s = (rgb_string or "").strip()
    if not s:
        return None
    c = QColor(s)
    if c.isValid():
        return c
    return None


class LayerStyle:
    """Maps Rules + Layer info to QPen/QBrush, owns per-layer visibility."""

    def __init__(self, rules):
        self.rules = rules
        self._pens = {}
        self._brushes = {}
        self._visible = {}
        self._init_visibility()

    def _init_visibility(self):
        for name, layer in self.rules.layers.items():
            if layer.material in SKIP_MATERIALS:
                self._visible[name] = False
            else:
                self._visible[name] = bool(layer.visible)

    def layer_names(self):
        names = []
        for name, layer in self.rules.layers.items():
            if layer.material in SKIP_MATERIALS:
                continue
            color = self._color(layer)
            if color is None:
                continue
            names.append(name)
        names.sort()
        return names

    def is_visible(self, name):
        return self._visible.get(name, True)

    def set_visible(self, name, vis):
        self._visible[name] = bool(vis)

    def _color(self, layer):
        if layer is None:
            return None
        return _qcolor(self.rules.colorTranslate(layer.color))

    def color(self, name):
        layer = self.rules.getLayer(name)
        return self._color(layer)

    def pen(self, name):
        if name in self._pens:
            return self._pens[name]
        layer = self.rules.getLayer(name)
        color = self._color(layer)
        if color is None:
            self._pens[name] = None
            return None
        c = QColor(color)
        c.setAlpha(200)
        pen = QPen(c, 0)
        pen.setCosmetic(True)
        self._pens[name] = pen
        return pen

    def brush(self, name):
        if name in self._brushes:
            return self._brushes[name]
        layer = self.rules.getLayer(name)
        color = self._color(layer)
        if color is None or layer is None:
            self._brushes[name] = QBrush(Qt.NoBrush)
            return self._brushes[name]
        if layer.nofill:
            self._brushes[name] = QBrush(Qt.NoBrush)
        else:
            c = QColor(color)
            c.setAlpha(120)
            self._brushes[name] = QBrush(c)
        return self._brushes[name]
