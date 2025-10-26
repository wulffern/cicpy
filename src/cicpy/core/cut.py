from .cell import Cell
from .rect import Rect
from .rules import Rules

class Cut(Cell):

    def __init__(self, startlayer:str, stoplayer:str, hcuts:int, vcuts:int):
        super().__init__(f"Cut_{startlayer}_{stoplayer}")
        self.startlayer = startlayer
        self.stoplayer = stoplayer
        self.hcuts = hcuts
        self.vcuts = vcuts
        self._build_placeholder_geometry()

    def _build_placeholder_geometry(self):
        try:
            rw = Rules.getInstance().get(self.stoplayer, "width")
        except Exception:
            rw = 0
        r = Rect(self.stoplayer, 0, 0, rw, rw)
        self.add(r)

    @staticmethod
    def getInstance(startlayer:str, stoplayer:str, hcuts:int, vcuts:int):
        return Cut(startlayer, stoplayer, hcuts, vcuts)

    @staticmethod
    def getCutsForRects(routeLayer:str, rects:list, cuts:int, vcuts:int, leftAlignCut:bool=True):
        rules = Rules.getInstance()
        cuts_out = []
        try:
            cw = rules.get(routeLayer, "width")
            cs = rules.get(routeLayer, "space")
        except Exception:
            cw = 0
            cs = 0
        for r in rects:
            if r is None:
                continue
            total_width = cuts*cw + (cuts-1)*cs if cuts > 0 else 0
            if leftAlignCut:
                x0 = r.x1
            else:
                x0 = r.x2 - total_width
            y0 = r.centerY() - (vcuts*cw + (vcuts-1)*cs)//2
            for iv in range(max(1, vcuts)):
                for ih in range(max(1, cuts)):
                    x = x0 + ih*(cw+cs)
                    y = y0 + iv*(cw+cs)
                    cuts_out.append(Rect(routeLayer, x, y, cw, cw))
        return cuts_out

