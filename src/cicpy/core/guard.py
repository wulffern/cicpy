from .cell import Cell
from .rect import Rect
from .rules import Rules

class Guard(Cell):

    def __init__(self, rect:Rect, layers:list):
        super().__init__("Guard")
        self.layers = list(layers or [])
        if rect:
            base = rect.getCopy()
            encx = Rules.getInstance().get("ROUTE","verticalgrid") if Rules.getInstance() else 0
            ency = encx
            base.adjust(encx)
            self.add(base)
            # For each requested layer, copy a rect
            for layer in self.layers:
                gr = base.getCopy(layer)
                self.add(gr)

    def getRect(self, layer:str):
        for c in self.children:
            if c.layer == layer:
                return c
        return None

