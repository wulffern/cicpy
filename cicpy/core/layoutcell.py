
from .rect import Rect
from .cell import Cell
from .port import Port
from .instance import Instance
from .text import Text

class LayoutCell(Cell):

    def __init__(self):
        super().__init__()

    def fromJson(self,o):
        super().fromJson(o)

        #- Handle subckt
        if("ckt" in o):

            pass

        for child in o["children"]:
            cl = child["class"]
            if(cl == "Rect"):
                c = Rect()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Port"):
                c  = Port()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Text"):
                c  = Text()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Instance"):
                c  = Instance()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Cell" or cl== "cIcCore::Route" or cl == "cIcCore::RouteRing" or cl == "cIcCore::Guard" or cl == "cIcCore::Cell"):
                l = LayoutCell()
                l.fromJson(child)
                self.add(l)
            else:
                print(f"Unkown class {cl}")
