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
            log.error(f"different number of nodes for {inst.name} "
                      f"({len(inst.nodes)}) and {inst.subcktName} "
                      f"({len(ckt.nodes)})")
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
        # Load Port / InstancePort / Rect children from JSON. Without this,
        # ``self.allports`` stays empty, ``LayoutCell.addToNodeGraph`` adds
        # nothing, and ``checkConnectivity`` reports no opens — the CLI
        # works only because it builds instances live via setSubcktInstance.
        from .port import Port
        from .rect import Rect
        for child in o.get("children", []):
            cl = child.get("class")
            c = None
            if cl in ("Port", "InstancePort"):
                # Reconstruct as Port — InstancePort needs constructor args
                # we don't have. Its CHILD NAME is carried across by hand
                # though: it is the only record of which child port this
                # parent net is wired to, and connectivity needs it to tell
                # one conductor named twice from two conductors shorted.
                c = Port()
            elif cl == "Rect":
                c = Rect()
            if c is None:
                continue
            c.design = self.design
            try:
                c.fromJson(child)
            except Exception:
                continue
            if child.get("childName"):
                c.childName = child["childName"]
            self.add(c)
        # Resolve the referenced layout cell. Without this,
        # ``_collectPhysicalRects`` never descends into the instance's body,
        # so metal/via rects inside primitive cells are invisible to the
        # connectivity check — every route landing on the same transistor
        # terminal looks like a separate component, producing aggressive
        # split-net reports.
        if self.cell and self.design is not None:
            cell_obj = self.design.cells.get(self.cell)
            if cell_obj is not None:
                self.layoutcell = cell_obj
                self._cell_obj = cell_obj

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
            rect.translate(*self._foldForChildren())
        elif self.angle == "MX":
            rect.mirrorX(0)
            rect.translate(*self._foldForChildren())
        else:
            #- R0: xcell is the load-origin correction, and whether the
            #- children need it depends on where the cell came from. A
            #- maglib cell was normalised at load -- it records
            #- `libshift` -- so instance position alone maps its
            #- children, and only getCellPoint (the painted use record)
            #- applies xcell. A cell REBUILT FROM JSON keeps its stored
            #- publish-frame children and still needs the correction
            #- here (measured: the maze-router fixture's pins moved by
            #- exactly the publish origin).
            if getattr(self.layoutcell, "libshift", None) is None:
                rect.translate(self.xcell, self.ycell)
        rect.translate(self.x1, self.y1)
        return rect

    def _foldForChildren(self):
        """The mirror fold, in the frame THE CHILDREN are already in.

        `xcell`/`ycell` fold about the cell's own box as the file
        states it, which is what the painted `use` record needs: magic
        mirrors the child's raw coordinates. A maglib cell's children,
        though, were normalised at load (it records `libshift`), so
        their frame starts at the origin and the fold about the raw
        box is off by exactly the cell's own x1/y1.

        For a cell whose box starts at its origin the two are the same
        number, which is why one attribute served both until a cell
        with a supply ring below y=0 was mirrored: the comparator
        pair's upper pins came back 24000 low, the two seam nets
        landed short of them and LVS called them open.
        """
        cell = self.layoutcell
        if cell is None or getattr(cell, "libshift", None) is None:
            return (self.xcell, self.ycell)
        return (self.xcell - int(cell.x1), self.ycell - int(cell.y1))

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
            #- y2, NOT y1 + y2, which is the same thing only for a
            #- cell whose box starts at its origin. A cell with a
            #- supply ring below y=0 has y1 < 0, and the extra term
            #- dropped the mirrored copy by exactly that much:
            #- LELO_TEMP_CCMP's upper comparator landed 24000 low,
            #- swallowed the 20000 seam gap the placer had left and
            #- overlapped the lower one by 4000 -- VDD, VSS and CMPO_B
            #- shorted. The fold that MY already uses (x2) says it
            #- correctly: the mirror puts the cell's far edge at the
            #- instance's origin.
            self.ycell = self.layoutcell.y2

        for child in self.children:
            child.translate(-self.x1, -self.y1)
            self._transformRect(child)

        self.updateBoundingRect()

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
