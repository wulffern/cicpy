######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-13
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

from .point import Point
from .cell import Cell
from .instanceport import InstancePort
import cicspi as spi
import logging
import re

class Instance(Cell):

    def __init__(self):
        super().__init__()
        self.instanceName = ""
        self.cell = ""
        self.layoutcell = None
        self.instancePorts = dict()
        self.instancePortsList = list()
        self.libpath = ""
        self.angle = ""
        self.xcell = 0
        self.ycell = 0

    def setSubcktInstance(self,inst:spi.SubcktInstance):

        log = logging.getLogger("Instance("+inst.subcktName + ")")
        self.instanceName = inst.name
        self.ports.clear()
        self.name = inst.subcktName

        if(self.layoutcell is None):
            log.warning("Could not find layoutcell " +inst.subcktName)
            return

        if(self.physicalOnly):
            return



        ckt = spi.Subckt.getSubckt(self.name)
        if(ckt is None):
            log.warning("Could not find subckt" + inst.subcktName)
            return


        if(len(inst.nodes) != len(ckt.nodes)):
            log.error("different number of nodes for " + inst.name + "(" + len(inst.nodes) + ") and" + inst.subcktName + "(" + len(ckt.nodes) + ")" )
            return


        for i in range(0,len(ckt.nodes)):
            instNode = inst.nodes[i]
            cktNode = ckt.nodes[i]
            cellPort = self.layoutcell.getPort(cktNode)
            if(cellPort):
                instPort = InstancePort(instNode,cellPort,self)
                # Track in instance port collections
                self.instancePorts[instNode] = instPort
                self.instancePortsList.append(instNode)
                self.add(instPort)
            else:
                log.warning(f"Could not find {cktNode} on {ckt.name}")

        pass
    
    def fromJson(self,o):
        super().fromJson(o)
        self.instanceName = o["instanceName"]
        self.angle = o["angle"]
        self.cell = o["cell"]
        if("libpath" in o):
            self.libpath = o["libpath"]
        self.xcell = o["xcell"]
        self.ycell = o["ycell"]

    def toJson(self):
        o = super().toJson()
        o["instanceName"] = self.instanceName
        o["angle"] = self.angle
        o["cell"] = self.cell
        o["libpath"] = self.libpath
        o["xcell"] = self.xcell
        o["ycell"] = self.ycell
        return o

    def isLayoutCell(self):
        c = self.getCell(self.cell)

        if(c is not None):
            return c.isLayoutCell()
        return False

    def findRectanglesByNode(self,node:str,filterChild:str):
        rects = list()
        for pi in self.children:
            if(pi is None):
                continue
            if(not pi.isInstancePort()):
                continue
            if(re.search(node, pi.name) and ((filterChild is None) or not re.search(filterChild, getattr(pi, 'childName', '')))):
                r = pi.get()
                if(r is not None):
                    r.parent = self
                    rects.append(r)
        return rects



    def getCellPoint(self):
        p = Point(self.x1 + self.xcell, self.y1 + self.ycell)
        return p

    def calcBoundingRect(self):

        if(self.layoutcell is None):
            return self

        r = self.layoutcell.getCopy()
        r.moveTo(self.x1,self.y1)
        return r

    def __str__(self):
        return  super().__str__() + " instanceName=%s xcell=%d ycell=%d angle=%s" %(self.instanceName,self.xcell,self.ycell,self.angle)
