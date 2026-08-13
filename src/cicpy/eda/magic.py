#!/usr/bin/env python3
######################################################################
##        Copyright (c) 2025 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2025-3-27
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

import re
import os
import cicpy as cic

class Magic(cic.LayoutCell):

    def __init__(self,techlib):
        super().__init__()
        self.magscale = 1
        self.techlib = techlib
        self.timestamp = 0
        #- WHAT THIS CELL PLACES. A .mag says its contents with `use`,
        #- and until now the reader kept only `rect`: a cell that
        #- places library cells came back as its own paint and nothing
        #- else. For a JNWTR standard cell that is its pins and its two
        #- M4 supply bars -- the M2 and M3 inside its M1-M4 via stacks
        #- are in the used cells, so every tool downstream reported the
        #- supply columns as free metal and the GDS was the first thing
        #- that knew otherwise (measured on LELO_TEMP_DIG).
        #-
        #- The uses are kept OUT of children on purpose: children is
        #- the cell's own content, and a placement, a bounding box, a
        #- port list and both writers all read it. This is an abstract
        #- view for asking what is in the way, and `flatMetal()` is how
        #- it is asked.
        self.uses = []
        self._pending_use = None
        self.dirname = ""
        self.bb_x1 = cic.INT_MAX
        self.bb_y1 = cic.INT_MAX
        self.bb_x2 = cic.INT_MIN
        self.bb_y2 = cic.INT_MIN
        self.found_bbox = False
        self.bboxRect = None
        self.ignoreBoundaryRouting = True
        self.rules = cic.Rules.getInstance()
        pass

    def toAngstrom(self,val):
        return int(val)/self.magscale*100

    def boxToRect(self,box,layer="PR"):
        r = cic.Rect(layer)
        r.x1 = self.toAngstrom(box[0])
        r.y1 = self.toAngstrom(box[1])
        r.x2 = self.toAngstrom(box[2])
        r.y2 = self.toAngstrom(box[3])
        return r

    def updateXYs(self,rect):
        x1 = self.toAngstrom(rect[0])
        y1 = self.toAngstrom(rect[1])
        x2 = self.toAngstrom(rect[2])
        y2 = self.toAngstrom(rect[3])

        if(x1 < self.bb_x1):
            self.bb_x1 = x1
        if(x2 > self.bb_x2):
            self.bb_x2 = x2
        if(y1 < self.bb_y1):
            self.bb_y1 = y1
        if(y2 > self.bb_y2):
            self.bb_y2 = y2

    
    def parseToken(self,token,category,line):

        #- Need to read all rectangles to get the bounding box
        #- for cells its use + transform + box (box is local, apply transform to move)

        if(category== ""):
            if(token == "magscale"):
                ar = line.split(" ")
                self.magscale = int(ar[1])
            #- Beginning of file
            pass
        elif(category == "properties"):
            if(line.startswith("FIXED_BBOX")):
                #print(line)
                bbox = re.findall(r"FIXED_BBOX\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",line)
                self.found_bbox = True
                self.bboxRect = self.boxToRect(bbox[0])

        elif(token == "flabel"):
            items = re.findall(r"(\S+)\s+s?\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+).*\s+(\S+)$",line)
            if(len(items) > 0):
                item = items[0]
                l = self.rules.aliasToLayer(item[0])
                x1 = self.toAngstrom(item[1])
                y1 = self.toAngstrom(item[2])
                x2 = self.toAngstrom(item[3])
                y2 = self.toAngstrom(item[4])
                r = cic.Rect(l.name)
                r.setPoint1(x1,y1)
                r.setPoint2(x2,y2)
                pname = items[0][-1].replace("[","<").replace("]",">")
                p = cic.Port(pname,routeLayer=l.name,rect=r)
                self.add(p)
        elif(token == "tech"):
            self.techlib = line
        elif(token == "use"):
            #- `use CELL INSTNAME`, then `transform a b c d e f`, then
            #- `box`. Only the transform is kept: the box is the used
            #- cell's own extent, which it can say for itself.
            ar = line.split()
            self._pending_use = ar[0] if ar else None
        elif(token == "transform" and self._pending_use):
            a, b, c, d, e, f = (int(v) for v in line.split()[:6])
            self.uses.append({"cell": self._pending_use,
                              "dx": self.toAngstrom(c),
                              "dy": self.toAngstrom(f),
                              "mx": a < 0, "my": e < 0})
            self._pending_use = None
        else:
            if(token == "rect"):
                rects = re.findall(r"(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",line)
                if(rects):

                    l = self.rules.aliasToLayer(category)
                    if(l is not None):
                        if l.material in (
                            cic.Material.METAL,
                            cic.Material.DIFFUSION,
                            cic.Material.POLY,
                            cic.Material.CUT,
                        ):
                            rect = rects[0]
                            x1 = self.toAngstrom(rect[0])
                            y1 = self.toAngstrom(rect[1])
                            x2 = self.toAngstrom(rect[2])
                            y2 = self.toAngstrom(rect[3])
                            r = cic.Rect(l.name)
                            r.setPoint1(x1,y1)
                            r.setPoint2(x2,y2)
                            self.add(r)

                    self.updateXYs(rects[0])
            pass


    def readFromFile(self,fname):
        if("border_" in fname):
            return
        self.name = os.path.basename(fname).replace(".mag","")
        lib = os.path.basename(os.path.dirname(fname))
        self.libpath = lib
        #- where its `use`d cells are: the same directory it came from
        self.dirname = os.path.dirname(fname)


        with open(fname) as fi:
            buff = ""
            pcount = 0
            ind =0
            category = ""
            for line in fi:
                #- Keep track of category
                m = re.search(r"<<\s+(\S+)\s+>>",line)
                if(m):
                    category = m.groups()[0]
                else:
                    arr = re.split(r"\s+",line)
                    token = arr[0]
                    rest = " ".join(arr[1:]).strip()
                    self.parseToken(token,category,rest)


        self.updateBoundingRect()
        #self.setRect(self.calcBoundingRect())


    def calcBoundingRect(self):
        if(self.found_bbox and self.ignoreBoundaryRouting):
            return self.bboxRect
        else:
            return super().calcBoundingRect()

    #- ---------------------------------------------------------------
    #- One SOURCE of hierarchy. The view over it is `Cell.flatMetal`,
    #- which every cell has: a .cic cell carries its hierarchy as
    #- instance children, and this one carries it as `use` records
    #- that the reader deliberately keeps out of children.
    #- ---------------------------------------------------------------

    def hiddenUses(self):
        """The cells this one places that `children` does not name."""
        out = []
        for u in self.uses:
            sub = self.resolveUse(u["cell"])
            if sub is not None:
                out.append((sub, int(u["dx"]), int(u["dy"]),
                            u["mx"], u["my"]))
        return out

    def resolveUse(self, cellname):
        """The cell a `use` names, read once and remembered."""
        cached = _USED.get(cellname)
        if cached is not None:
            return cached if cached is not _MISSING else None
        fname = os.path.join(self.dirname, cellname + ".mag")
        if not os.path.exists(fname):
            _USED[cellname] = _MISSING
            self.log.warning(f"{self.name}: uses {cellname}, which is "
                             f"not in {self.dirname}")
            return None
        sub = Layout(self.techlib)
        sub.readFromFile(fname)
        _USED[cellname] = sub
        return sub


#- one read per library cell per process: a strip of eight standard
#- cells names the same four device cells forty times over
_MISSING = object()
_USED = {}




class Layout(Magic):
    pass
