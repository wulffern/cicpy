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
from .rect import Rect
from .rules import Rules
import cicspi as spi
import logging
import re


class TerminalAccess:

    def __init__(self, terminal_name, source_layer, target_layer, port_rect, connected_rects, access_rects):
        self.terminalName = terminal_name
        self.sourceLayer = source_layer
        self.targetLayer = target_layer
        self.portRect = port_rect
        self.connectedRects = connected_rects
        self.accessRects = access_rects

    def primary(self, anymetal=False):
        if not anymetal and self.portRect is not None:
            return self.portRect.getCopy(self.sourceLayer)
        if self.accessRects:
            return self.accessRects[0]
        if self.portRect is not None:
            return self.portRect.getCopy(self.sourceLayer)
        return None

    def isEmpty(self):
        return len(self.accessRects) == 0


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
        self._cell_obj = None  # Direct reference to Cell object
    
    def setCell(self, cell):
        """Set the cell - accepts either a Cell object or a string name"""
        if isinstance(cell, str):
            # String name - look up in design
            self.cell = cell
            self._cell_obj = self.getCell(cell)
            if self._cell_obj:
                self.name = self._cell_obj.name
                self.updateBoundingRect()
        else:
            # Cell object - store directly
            self._cell_obj = cell
            if cell:
                self.cell = cell.name
                self.name = cell.name
                self.updateBoundingRect()

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
            primitive_ports = []
            if self.layoutcell is not None and hasattr(self.layoutcell, "parent") and hasattr(self.layoutcell.parent, "getPrimitivePortOrder"):
                primitive_ports = self.layoutcell.parent.getPrimitivePortOrder(inst.subcktName)
            if primitive_ports and len(inst.nodes) == len(primitive_ports):
                for idx, port_name in enumerate(primitive_ports):
                    instNode = inst.nodes[idx]
                    cellPort = self.layoutcell.getPort(port_name)
                    if cellPort is None:
                        continue
                    instPort = InstancePort(instNode,cellPort,self)
                    self.instancePorts[instNode] = instPort
                    self.instancePortsList.append(instNode)
                    self.add(instPort)
                return
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
        # Use direct cell reference if available (e.g., for InstanceCut)
        if hasattr(self, '_cell_obj') and self._cell_obj is not None:
            return self._cell_obj.isLayoutCell()
        
        # Otherwise look up by name
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

    def getOccupiedRectangles(self, layer: str):
        rects = []
        if self.layoutcell is None:
            return rects

        for child in self.layoutcell.children:
            if child is None:
                continue
            if not child.isRect():
                continue
            if child.layer != layer:
                continue
            rr = child.getCopy()
            self._transformRect(rr)
            rr.parent = self
            rects.append(rr)
        return rects

    def _transformRect(self, rect):
        if rect is None:
            return None
        if self.angle == "R90":
            rect.rotate(90)
            rect.translate(self.xcell, self.ycell)
        elif self.angle == "MY":
            rect.mirrorY(0)
            rect.translate(self.xcell, self.ycell)
        elif self.angle == "MX":
            rect.mirrorX(0)
            rect.translate(self.xcell, self.ycell)
        rect.translate(self.x1, self.y1)
        return rect

    def setAngle(self, angle: str):
        self.angle = angle or ""
        self.xcell = 0
        self.ycell = 0
        if self.layoutcell is None:
            return
        if self.angle == "R90":
            self.xcell = self.layoutcell.y2
        elif self.angle == "MY":
            self.xcell = self.layoutcell.x2
        elif self.angle == "MX":
            self.ycell = self.layoutcell.y1 + self.layoutcell.y2

        for child in self.children:
            child.translate(-self.x1, -self.y1)
            self._transformRect(child)

        self.updateBoundingRect()

    def _normalizeLayerName(self, layer_name):
        rules = Rules.getInstance()
        if rules is None or layer_name is None:
            return layer_name
        if layer_name in rules.layers:
            return rules.layers[layer_name].name
        if hasattr(rules, "alias") and layer_name in rules.alias:
            return rules.alias[layer_name].name
        return layer_name

    def _rectsOverlapOrTouch(self, rect1, rect2):
        if rect1 is None or rect2 is None:
            return False
        if rect1.x2 < rect2.x1 or rect2.x2 < rect1.x1:
            return False
        if rect1.y2 < rect2.y1 or rect2.y2 < rect1.y1:
            return False
        return True

    def _layersCanConnect(self, layer1, layer2):
        l1 = self._normalizeLayerName(layer1)
        l2 = self._normalizeLayerName(layer2)
        if l1 == l2:
            return True

        rules = Rules.getInstance()
        if rules is None:
            return False

        next1 = self._normalizeLayerName(rules.getNextLayer(l1))
        prev1 = self._normalizeLayerName(rules.getPreviousLayer(l1))
        next2 = self._normalizeLayerName(rules.getNextLayer(l2))
        prev2 = self._normalizeLayerName(rules.getPreviousLayer(l2))

        return l2 in (next1, prev1) or l1 in (next2, prev2)

    def _collectConnectedCellRects(self, seed_rect):
        if self.layoutcell is None or seed_rect is None:
            return []

        candidates = []
        for child in self.layoutcell.children:
            if child is None:
                continue
            if not child.isRect():
                continue
            if child.isPort() or child.isText():
                continue
            candidates.append(child)

        connected = []
        queue = [seed_rect]
        visited = set()

        while queue:
            current = queue.pop(0)
            for idx, candidate in enumerate(candidates):
                if idx in visited:
                    continue
                if not self._rectsOverlapOrTouch(current, candidate):
                    continue
                if not self._layersCanConnect(current.layer, candidate.layer):
                    continue
                visited.add(idx)
                connected.append(candidate)
                queue.append(candidate)

        return connected

    def getTerminalAccess(self, terminal_name: str, target_layer: str = "M1"):
        if self.layoutcell is None:
            return None

        port = self.layoutcell.getPort(terminal_name)
        if port is None:
            return None

        port_rect = port.get()
        if port_rect is None:
            return None

        port_rect = port_rect.getCopy()
        source_layer = self._normalizeLayerName(port_rect.layer)
        target_layer = self._normalizeLayerName(target_layer or source_layer)
        port_rect.layer = source_layer

        connected_rects = self._collectConnectedCellRects(port_rect)
        access_rects = []
        seen = set()
        for rect in connected_rects:
            if self._normalizeLayerName(rect.layer) != target_layer:
                continue
            rr = rect.getCopy(target_layer)
            self._transformRect(rr)
            key = (rr.layer, rr.x1, rr.y1, rr.x2, rr.y2)
            if key in seen:
                continue
            seen.add(key)
            access_rects.append(rr)

        translated_port = port_rect.getCopy(source_layer)
        self._transformRect(translated_port)
        if source_layer == target_layer:
            key = (translated_port.layer, translated_port.x1, translated_port.y1, translated_port.x2, translated_port.y2)
            if key not in seen:
                seen.add(key)
                access_rects.insert(0, translated_port.getCopy(target_layer))
        translated_connected = []
        for rect in connected_rects:
            rr = rect.getCopy(self._normalizeLayerName(rect.layer))
            self._transformRect(rr)
            translated_connected.append(rr)

        return TerminalAccess(
            terminal_name,
            source_layer,
            target_layer,
            translated_port,
            translated_connected,
            access_rects,
        )



    def getCellPoint(self):
        p = Point(self.x1 + self.xcell, self.y1 + self.ycell)
        return p

    def calcBoundingRect(self):
        # Use direct cell reference if available (e.g., for InstanceCut)
        cell_to_use = None
        if hasattr(self, '_cell_obj') and self._cell_obj is not None:
            cell_to_use = self._cell_obj
        elif self.layoutcell is not None:
            cell_to_use = self.layoutcell
        
        if cell_to_use is None:
            # No cell set, return self as bounding rect
            return self

        r = cell_to_use.calcBoundingRect()
        if self.angle == "R90":
            r.rotate(90)
        elif self.angle == "MY":
            r.mirrorY(0)
            r.translate(self.xcell, self.ycell)
        elif self.angle == "MX":
            r.mirrorX(0)
            r.translate(self.xcell, self.ycell)
        r.moveTo(self.x1, self.y1)
        return r

    def __str__(self):
        return  super().__str__() + " instanceName=%s xcell=%d ycell=%d angle=%s" %(self.instanceName,self.xcell,self.ycell,self.angle)
