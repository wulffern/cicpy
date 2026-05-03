######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView, QRubberBand


PAN_STEP = 50  # scene units per arrow key
ZOOM_FACTOR = 1.2


class LayoutView(QGraphicsView):

    cursorMoved = Signal(float, float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Y-flip so layout Y grows up.
        self.scale(1, -1)
        self._fitted = False
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._rubber_origin = None

    def set_scene(self, scene):
        self.setScene(scene)
        self._fitted = False
        self.fit()

    def fit(self):
        scene = self.scene()
        if scene is None:
            return
        rect = scene.sceneRect()
        if rect.isEmpty():
            rect = scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        self.fitInView(rect, Qt.KeepAspectRatio)
        self._fitted = True

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:
            self.fit()

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_F:
            self.fit()
            return
        if k == Qt.Key_Z:
            if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
                self._zoom(1.0 / ZOOM_FACTOR)
            else:
                self._zoom(ZOOM_FACTOR)
            return
        if k == Qt.Key_Up:
            self._pan(0, PAN_STEP)
            return
        if k == Qt.Key_Down:
            self._pan(0, -PAN_STEP)
            return
        if k == Qt.Key_Left:
            self._pan(PAN_STEP, 0)
            return
        if k == Qt.Key_Right:
            self._pan(-PAN_STEP, 0)
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        mods = event.modifiers()
        delta = event.angleDelta().y()
        if mods & (Qt.ControlModifier | Qt.MetaModifier):
            if delta > 0:
                self._zoom(ZOOM_FACTOR)
            elif delta < 0:
                self._zoom(1.0 / ZOOM_FACTOR)
            return
        if mods & Qt.ShiftModifier:
            self._pan(-delta, 0)
            return
        # Default: vertical scroll behaves like normal pan.
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._rubber_origin = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._rubber_origin, QSize()))
            self._rubber_band.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._rubber_origin is not None:
            self._rubber_band.setGeometry(QRect(self._rubber_origin, pos).normalized())
        sp = self.mapToScene(pos)
        self.cursorMoved.emit(sp.x(), sp.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._rubber_origin is not None:
            rect = QRect(self._rubber_origin, event.position().toPoint()).normalized()
            self._rubber_band.hide()
            self._rubber_origin = None
            if rect.width() > 5 and rect.height() > 5:
                scene_rect = self.mapToScene(rect).boundingRect()
                self.fitInView(scene_rect, Qt.KeepAspectRatio)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _zoom(self, factor):
        self.scale(factor, factor)

    def _pan(self, dx, dy):
        h = self.horizontalScrollBar()
        v = self.verticalScrollBar()
        h.setValue(h.value() - int(dx))
        v.setValue(v.value() + int(dy))
