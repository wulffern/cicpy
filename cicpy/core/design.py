
from .rect import Rect
from .cell import Cell
from .layoutcell import LayoutCell
import json

class Design(Cell):

    def fromJsonFile(self,fname):
        jobj = None
        with open(fname,"r") as f:
            jobj = json.load(f)
        for o in jobj["cells"]:
            c = LayoutCell()
            c.fromJson(o)
            c.rotate(1000)
            self.add(c)
            


        