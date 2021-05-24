######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-14
## ###################################################################
##  The MIT License (MIT)
## 
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
## 
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
## 
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##  
######################################################################

from .rect import Rect
from .cell import Cell
from .port import Port
from .instance import Instance
from .text import Text
from ..ckt.subckt import Subckt

class LayoutCell(Cell):

    def __init__(self):
        super().__init__()
        self.ckt = None

        self.altenateGroup = False
        self.boundaryIgnoreRouting = False
        self.useHalfHeight = False


    def toJson(self):
        o = super().toJson()

        return o

    def fromJson(self,o):
        super().fromJson(o)

        #- Handle subckt
        if("ckt" in o):
            self.ckt = Subckt()
            self.ckt.fromJson(o["ckt"])


        if("alternateGroup" in o):
            self.alternateGroup = o["alternateGroup"]

        if("useHalfHeight" in o):
            self.useHalfHeight = o["useHalfHeight"]

        if("boundarIgnoreRouting" in o):
            self.boundaryIgnoreRouting = o["boundaryIgnoreRouting"]

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
