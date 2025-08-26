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
import re
import logging


class LayoutCell(Cell):

    def __init__(self):
        super().__init__()
        #self.rules = rules
        self.altenateGroup = False
        self.boundaryIgnoreRouting = False
        self.useHalfHeight = False
        self.graph = None
        self.um = 10000
        self.log = logging.getLogger("LayoutCell")
        self.dummyCounter = 0
        rules = Rules.getInstance()
        if(rules.hasRules()):
            space =rules.get("CELL","space")
            self.place_groupbreak = [100]
            self.place_xspace = [space]
            self.place_yspace = [space]



    def addInstance(self,cktInst,x:int,y:int):

        if(cktInst is None):
            return

        i = Instance()
        layoutCell = self.parent.getLayoutCell(cktInst.subcktName)
        i.cell = layoutCell.name
        i.layoutcell = layoutCell
        i.libpath = layoutCell.libpath
        i.setSubcktInstance(cktInst)

        self.add(i)
        i.moveTo(x,y)
        self.addToNodeGraph(i)
        i.updateBoundingRect()
        return i

    def addToNodeGraph(self,inst):

        if (inst is None): return

        allp = inst.allports
        keys = inst.allPortNames

        for s in keys:
            for p in allp:
                if(p is None): continue
                if(self.nodeGraph.contains(p.name)):
                    self.nodeGraph[p.name].append(p)
                else:
                    g = Graph()
                    g.name = p.name
                    g.append(p)
                    self.nodeGraphList.append(p.name)
                    self.nodeGraph[p.name] = g


        
        pass

    def toJson(self):
        o = super().toJson()
        return o

    def getInstancesByName(self,regex):
        data = list()
        for c in self.children:
            if(c.isInstance()):
                if(re.search(regex,c.name)):
                    data.append(c)
        return data

    def getInstancesByCellname(self,regex):
        data = list()
        for c in self.children:
            if(c.isInstance()):
                if(re.search(regex,c.cell)):
                    data.append(c)
        return data

    def getDummyInst(self,subcktName,repl):
        name = None
        if(re.search(r"CH_\d+C\d+F\d+",self.name)):
            name =  re.sub(r"C\d+F\d+",repl,subcktName)

        if(name is not None):
            si = SubcktInstance()
            si.subcktName = name
            si.name = "xdmy__"  + str(self.dummyCounter)
            self.dummyCounter += 1
            return si

        return None

    def getDummyBottomInst(self,subcktName):
        return self.getDummyInst(subcktName,"CTAPBOT")

    def getDummyTopInst(self,subcktName):
        return self.getDummyInst(subcktName,"CTAPTOP")

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

            name = inst.name
            group = inst.groupName
            if(group != prevgroup or prevgroup == ""):
                startGroup = True
                if(previnst is not None):
                    dname = self.getDummyTopInst(inst.subcktName)
                    if(dname is not None):
                        dummy = self.addInstance(dname,x,y)
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
                dname = self.getDummyBottomInst(inst.subcktName)
                if(dname is not None):
                    dummy = self.addInstance(dname,x,y)
                    x = dummy.x1
                    y = dummy.y2

            linst = self.addInstance(inst,x,y)
            if(linst.x2 > next_x):
                next_x = linst.x2
            next_y = linst.y2

            if(next_y > ymax):
                ymax = next_y

            x = linst.x1
            y = next_y

            prevcell = linst
            previnst = inst

            prevgroup = group
            first = False
            startGroup = False


        if(previnst is not None):
             dname = self.getDummyTopInst(inst.subcktName)
             if(dname is not None):
                 dummy = self.addInstance(dname,x,y)
                 x = dummy.x1
                 y = dummy.y2
                 next_y = y
        pass

    def route(self):

        pass


    def paint(self):

        pass

    def findRectanglesByNode(self,node:str,filterChild:str=None,matchInstance:str=None):
        rects = list()
        for i in self.children:
            if(i is None): continue
            if(not i.isInstance()): continue

            if(matchInstance is not None):
                if(not re.search(matchInstance,i.name)): continue

            childRects = i.findRectanglesByNode(node,filterChild)
            for r in childRects:
                rects.append(r)
        return rects


    def addAllPorts(self):
        if(self.subckt is None): return
        nodes = self.subckt.nodes

        for node in nodes:

            if(node in self.ports): continue
            rects = self.findRectanglesByNode("^" + node + "$",None,None)
            if(len(rects) > 0):
                self.updatePort(node,rects[0])
            else:
                self.log.warning(r"No rects found on " + node)

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
                self.log.warning(f"Unkown class {cl}")

            if(c is not None):
                c.design = self.design
                c.fromJson(child)
                self.add(c)
