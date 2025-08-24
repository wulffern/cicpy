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
from .rules import Rules
from .instance import Instance
from .text import Text
import cicspi as spi


class LayoutCell(Cell):

    def __init__(self):
        super().__init__()
        #self.rules = rules
        self.altenateGroup = False
        self.boundaryIgnoreRouting = False
        self.useHalfHeight = False
        self.graph = None
        rules = Rules()
        if(rules.hasRules()):
            space =rules.get("CELL","space")
            #print(space)
            self.place_groupbreak = [100]
            self.place_xspace = [space]
            self.place_yspace = [space]

    def toJson(self):
        o = super().toJson()
        return o


    def place(self):

        um = 10000

        next_gbreak = self.place_groupbreak.pop(0)
        next_xspace = self.place_xspace.pop(0)
        next_yspace = self.place_yspace.pop(0)

        next_x = 0
        next_y = 0

        prevgroup = ""

        ymax = 0
        yorg = 0
        xorg = 0

        groupcount = 0
        first = True
        startGroup = False
        endGroup = False
        prevcell = None
        previnst = None

        for inst in self.ckt.orderInstancesByGroup():

            lcell = self.parent.getInstance(inst)
            name = inst.name
            group = inst.groupName
            if(group != prevgroup or prevgroup == ""):
                startGroup = True
                if(previnst is not None):
                    dummy = self.parent.getInstanceDummyTop(previnst)
                    if(dummy is not None):
                        print("Placing dummy",inst.subcktName)
                        dummy.moveTo(x,y)
                        self.add(dummy)
                        x = dummy.x1
                        y = dummy.y2
                        next_y = y
                if(next_y > ymax):
                    ymax = next_y
                if(next_gbreak == groupcount):
                    y = ymax + next_yspace
                    yorg = y
                    if(len(self.place_groupbreak) > 0):
                        next_gbreak = int(self.place_groupbreak.pop(0))
                    x = 0
                else:
                    y = yorg

                if(first):
                    x = 0
                else:
                    x = next_x + next_xspace
                    if(len(self.place_xspace) > 0):
                        next_xspace = int(self.place_xspace.pop(0))

                groupcount += 1

            if(startGroup):
                dummy = self.parent.getInstanceDummyBottom(inst)
                if(dummy is not None):
                    dummy.moveTo(x,y)
                    self.add(dummy)
                    x = dummy.x1
                    y = dummy.y2

            lcell.moveTo(x,y)

            self.add(lcell)

            if(lcell.x2 > next_x):
                next_x = lcell.x2
            next_y = lcell.y2

            if(next_y > ymax):
                ymax = next_y

            x = lcell.x1
            y = next_y

            prevcell = lcell
            previnst = inst

            prevgroup = group
            first = False
            startGroup = False


        if(previnst is not None):
            dummy = self.parent.getInstanceDummyTop(previnst)
            if(dummy is not None):
                print("Placing dummy",inst.subcktName)
                dummy.moveTo(x,y)
                self.add(dummy)
                x = dummy.x1
                y = dummy.y2
                next_y = y
        pass

    def route():

        pass

    def fromJson(self,o):
        super().fromJson(o)

        if("alternateGroup" in o):
            self.alternateGroup = o["alternateGroup"]

        if("useHalfHeight" in o):
            self.useHalfHeight = o["useHalfHeight"]

        if("boundarIgnoreRouting" in o):
            self.boundaryIgnoreRouting = o["boundaryIgnoreRouting"]

        if("meta" in o):
            self.meta = o["meta"]

        if("graph" in o):
            self.graph = o["graph"]

        for child in o["children"]:

            c = None
            cl = child["class"]
            if(cl == "Rect"):
                c = Rect()
            elif(cl == "Port"):
                c  = Port()
            elif(cl == "Text"):
                c  = Text()
            elif(cl == "Instance"):
                c  = Instance()
            elif(cl == "Cell" or cl== "cIcCore::Route" or cl == "cIcCore::RouteRing" or cl == "cIcCore::Guard" or cl == "cIcCore::Cell" or cl == "cIcCore::LayoutCell"):
                c = LayoutCell()
            else:
                print(f"Unkown class {cl}")

            if(c is not None):
                c.design = self.design
                c.fromJson(child)
                self.add(c)
