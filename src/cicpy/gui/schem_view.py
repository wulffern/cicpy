######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QRubberBand

from .panzoom_view import PAN_STEP, PanZoomView, ZOOM_FACTOR  # noqa: F401

_LASSO_MIN_DRAG = 5  # pixels before treating left-press+move as a lasso


class SchemView(PanZoomView):
    """Schematic view: PanZoomView with Y down (xschem's frame), plus
    the left-drag lasso selection over component groups."""

    Y_UP = False

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        # Lasso (left-button drag in empty space) state
        self._lasso_origin = None
        self._lasso_active = False
        self._lasso_band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._lasso_additive = False

    def mousePressEvent(self, event):
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
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
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
