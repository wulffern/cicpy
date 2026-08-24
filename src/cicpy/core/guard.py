import logging

from .cell import Cell
from .rect import Rect
from .cut import Cut


class Guard(Cell):
    """cIcCore::Guard: a guard ring around `rect`.

    Four sides of OD+M1 (plus the enclosing layers), each side filled
    with contacts. The ring geometry keys off a 2x1 OD-M1 cut template:
    its OD offset and height set the strap width, and its total height
    grows the incoming rect so the ring sits outside what it guards.
    """

    def __init__(self, rect: Rect, layers: list):
        #- the reference Guard carries NO name -- with a prefix it
        #- serializes as the bare prefix, and the goldens show exactly that
        super().__init__()
        self.layers = list(layers or [])
        log = logging.getLogger("Guard")

        if rect is None:
            return

        d1 = Cut("OD", "M1", 2, 1)
        od = d1.getRect("OD")
        if od is None:
            log.warning("Could not find OD rectangle in Cut")
            return

        xod = od.x1 - d1.x1
        yod = od.y1 - d1.y1
        odw = od.height()

        d1.addEnclosingLayers(self.layers)

        r = rect
        h = d1.height()
        r.adjust(-h, -h, h, h)

        c_bot = Cell()
        c_bot.add(Rect("OD", r.x1 + xod, r.y1 + yod, r.width() - xod*2, odw))
        c_bot.add(Rect("M1", r.x1 + xod, r.y1 + yod, r.width() - xod*2, odw))
        c_left = Cell()
        c_left.add(Rect("OD", r.x1 + xod, r.y1 + yod, odw, r.height() - yod*2))
        c_left.add(Rect("M1", r.x1 + xod, r.y1 + yod, odw, r.height() - yod*2))
        c_top = Cell()
        c_top.add(Rect("OD", r.x1 + xod, r.y1 + r.height() - yod - odw, r.width() - xod*2, odw))
        c_top.add(Rect("M1", r.x1 + xod, r.y1 + r.height() - yod - odw, r.width() - xod*2, odw))
        c_right = Cell()
        c_right.add(Rect("OD", r.x1 + r.width() - xod - odw, r.y1 + yod, odw, r.height() - yod*2))
        c_right.add(Rect("M1", r.x1 + r.width() - xod - odw, r.y1 + yod, odw, r.height() - yod*2))

        self.add(Rect("M1", r.x1 + xod, r.y1 + yod, r.width() - xod*2, odw))

        for c2 in (c_bot, c_top, c_left, c_right):
            rcp = c2.getCopy()
            if rcp.isVertical():
                rcp.adjust(0, odw, 0, -odw)
            else:
                rcp.adjust(odw, 0, -odw, 0)

            self.add(Cut.getFillCell("OD", "M1", rcp))

            c2.addEnclosingLayers(self.layers)
            self.add(c2)
