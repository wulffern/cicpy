######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import QGraphicsView, QRubberBand


PAN_STEP = 50
ZOOM_FACTOR = 1.2
_LASSO_MIN_DRAG = 5  # pixels before treating left-press+move as a lasso


class SchemView(QGraphicsView):
    """Schematic view — same UX as LayoutView but no Y-flip (xschem grows Y down)."""

    cursorMoved = Signal(float, float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self._fitted = False
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._rubber_origin = None
        # Lasso (left-button drag in empty space) state
        self._lasso_origin = None
        self._lasso_active = False
        self._lasso_band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._lasso_additive = False

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
            self._pan(0, -PAN_STEP)
            return
        if k == Qt.Key_Down:
            self._pan(0, PAN_STEP)
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
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._rubber_origin = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._rubber_origin, QSize()))
            self._rubber_band.show()
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            # Track origin so we can decide click vs lasso on move.
            scene = self.scene()
            if scene is not None:
                sp = self.mapToScene(event.position().toPoint())
                # Skip text labels — they're click-through.
                from PySide6.QtWidgets import QGraphicsSimpleTextItem
                hit = None
                for it in scene.items(sp):
                    if isinstance(it, QGraphicsSimpleTextItem):
                        continue
                    hit = it
                    break
                # Walk up to a tagged component group; if we hit one, this is
                # a click — let the scene handle it normally.
                comp = None
                cur = hit
                while cur is not None:
                    if cur.data(1) is not None and cur.data(0):
                        comp = cur
                        break
                    cur = cur.parentItem()
                if comp is None:
                    self._lasso_origin = event.position().toPoint()
                    self._lasso_active = False
                    self._lasso_additive = bool(event.modifiers() & Qt.ShiftModifier)
                    # Don't accept yet — if it's a click (no drag), the scene
                    # still gets the press for clear-selection semantics.
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._rubber_origin is not None:
            self._rubber_band.setGeometry(QRect(self._rubber_origin, pos).normalized())
        if self._lasso_origin is not None and event.buttons() & Qt.LeftButton:
            dx = pos.x() - self._lasso_origin.x()
            dy = pos.y() - self._lasso_origin.y()
            if not self._lasso_active and (abs(dx) + abs(dy)) > _LASSO_MIN_DRAG:
                self._lasso_active = True
                self._lasso_band.setGeometry(QRect(self._lasso_origin, QSize()))
                self._lasso_band.show()
            if self._lasso_active:
                self._lasso_band.setGeometry(
                    QRect(self._lasso_origin, pos).normalized())
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
        if event.button() == Qt.LeftButton and self._lasso_origin is not None:
            if self._lasso_active:
                rect = QRect(self._lasso_origin, event.position().toPoint()).normalized()
                self._lasso_band.hide()
                scene_rect = self.mapToScene(rect).boundingRect()
                scene = self.scene()
                if scene is not None and hasattr(scene, "components_in_rect"):
                    comps = scene.components_in_rect(scene_rect)
                    scene.select_components(comps, additive=self._lasso_additive)
                self._lasso_active = False
                self._lasso_origin = None
                event.accept()
                return
            self._lasso_origin = None
        super().mouseReleaseEvent(event)

    def _zoom(self, factor):
        self.scale(factor, factor)

    def _pan(self, dx, dy):
        h = self.horizontalScrollBar()
        v = self.verticalScrollBar()
        h.setValue(h.value() - int(dx))
        v.setValue(v.value() + int(dy))
