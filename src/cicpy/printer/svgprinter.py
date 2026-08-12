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
from .designprinter import DesignPrinter
import sys
import svgwrite
import numpy as np
from os import path
import logging
import os
import re


log = logging.getLogger("SvgPrinter")

svgcells = dict()
#- which cells each cell draws, so a definition can bring its own
#- subtree along
svgdeps = dict()

class SvgCell(svgwrite.Drawing):

    def translate(self,angstrom):
        return (angstrom/10)/self.scale

    def __init__(self,fname,cell,scale,x,y,**args):
        self.cell = cell
        self.scale = scale
        self.refs = dict()
        self.topgr = svgwrite.container.Group(transform=f"translate({x},{y}) ")
        self.gr = svgwrite.container.Group(id=self.cell.name)
        self.topgr.add(self.gr)
        svgcells[cell.name] = self

        x1 = self.translate(cell.x1) + x
        y1 = self.translate(cell.y1) + y
        x2 = self.translate(cell.x2) + x + x
        y2 = self.translate(cell.y2) + y + y


        super().__init__(fname,profile='tiny',size=(x2,y2),viewBox=(f"0 0 {x2} {y2}"),**args)

    def closeAndSave(self):
        self.add(self.topgr)
        self.save()


    def addFlight(self, rects, color, label):
        """Box each pin of a net and join them with a dashed line.

        WHAT SHOULD BE CONNECTED, drawn on top of what is. A net that
        the router has not closed looks exactly like one it has until
        someone traces it by hand; a flightline says "these two belong
        together" and the picture then shows whether any metal does it.

        This is the loop that got LELO_TEMP_BIAS's LPI written: draw
        the overlay, look, write the story, repeat.
        """
        pts = []
        for r in rects:
            x1, x2 = self.translate(r.x1), self.translate(r.x2)
            y1, y2 = self.translate(r.y1), self.translate(r.y2)
            self.gr.add(self.rect(insert=(x1, y1),
                                  size=(max(x2 - x1, 0.4), max(y2 - y1, 0.4)),
                                  fill="none", stroke=color,
                                  stroke_width=0.6))
            pts.append(((x1 + x2) / 2, (y1 + y2) / 2))
        for p in pts[1:]:
            self.gr.add(self.line(start=pts[0], end=p, stroke=color,
                                  stroke_width=0.7,
                                  stroke_dasharray="2,1.4"))
        if pts:
            #- the label is drawn flipped, because the raster is flipped
            #- back by the caller so that y points up
            t = self.text(label, insert=(pts[0][0] + 1, pts[0][1]),
                          fill=color, font_size=4)
            t.rotate(180, center=(pts[0][0] + 1, pts[0][1]))
            t.scale(-1, 1)
            self.gr.add(t)

    def addRect(self,r,color,fill):
        x1 = self.translate(r.x1)
        x2 = self.translate(r.x2)
        y1 = self.translate(r.y1)
        y2 = self.translate(r.y2)

        if(fill == "nofill"):
            r = self.rect((x1,y1),(x2-x1,y2-y1),stroke=color,stroke_width=0.1,fill_opacity=0.6)
        else:
            r = self.rect((x1,y1),(x2-x1,y2-y1),fill=color,stroke=color,stroke_width=0.1,fill_opacity=0.6)

        
        self.gr.add(r)

    def addText(self, t, color="black"):
        x = self.translate(t.x1)
        y = self.translate(t.y1)
        txt = self.text(t.name, insert=(x, y), fill=color, font_size=8)
        self.gr.add(txt)

    @staticmethod
    def _defsFor(name, seen=None):
        """`name` and every cell it draws, deepest first."""
        seen = seen if seen is not None else set()
        if name in seen:
            return []
        seen.add(name)
        out = []
        for dep in sorted(svgdeps.get(name, ())):
            out += SvgCell._defsFor(dep, seen)
        out.append(name)
        return out

    def addRef(self,inst):

        svgdeps.setdefault(self.cell.name, set()).add(inst.name)
        p = inst.getCellPoint()
        x = self.translate(p.x)
        y = self.translate(p.y)

        transform = f"translate({x},{y})"

        rotation = inst.angle
        #- The mirrors are the ones a matched pair uses, and they say
        #- the same thing here as in Instance.calcBoundingRect: MY
        #- flips x about the cell point, MX flips y. MX used to fall
        #- through to a print() and be drawn UNMIRRORED on top of the
        #- neighbour it was mirrored away from -- measured on
        #- LELO_TEMP_CCMP, where the upper comparator vanished.
        if(rotation == "MY"):
            transform = transform + " scale(-1,1) "
        elif(rotation == "MX"):
            transform = transform + " scale(1,-1) "
        elif(rotation == "R180"):
            transform = transform + " scale(-1,-1) "
        elif(rotation in ("", "R0")):
            pass
        else:
            log.warning(f"instance rotation {rotation!r} not implemented; "
                        f"{inst.name} drawn unrotated")
        
        if(inst.name not in self.refs):
            if(inst.name not in svgcells):
                #- A DANGLING REFERENCE IS NOT A CRASH. An instance can
                #- name a cell no file defines -- measured,
                #- rey_tr_sky130a's library references "REYTR_", which
                #- exists nowhere -- and one of those took the whole
                #- render down with a KeyError. Draw the rest and say
                #- what is missing; a picture with a hole in it is more
                #- use than no picture.
                log.warning(f"no cell {inst.name!r} to draw; skipped")
                return
            #- REFERENCE THE CELL'S GROUP, not the whole drawing it
            #- lives in. Embedding the other SvgCell put a nested
            #- <svg>, viewBox and all, between the definition and the
            #- <use> -- and a viewport of its own is a transform of its
            #- own: rsvg drew the mirrored comparator of LELO_TEMP_CCMP
            #- correctly, cairosvg dropped the scale and placed it a
            #- whole cell height too high. A <g> in <defs> is what
            #- <use> is specified against, and both agree on it.
            #-
            #- The nested drawing carried the whole subtree with it,
            #- so a group alone leaves its own <use>s pointing at
            #- nothing: every cell BELOW this one has to be defined
            #- here too.
            for dep in self._defsFor(inst.name):
                if dep in self.refs or dep not in svgcells:
                    continue
                g = svgwrite.container.Group(id=dep + "_inst", opacity=0)
                g.add(svgcells[dep].gr)
                self.defs.add(g)
                self.refs[dep] = g


        use = svgwrite.container.Use("#"+inst.name,transform=transform )
        self.gr.add(use)



class SvgPrinter(DesignPrinter):

    #- an SVG <use> can only name a group that has already been
    #- written, so the cells have to come out bottom up
    orderByDependency = True

    def __init__(self,filename,rules,scale,x,y,flightnets=None):
        super().__init__(filename,rules)
        self.x = x
        self.y = y
        self.scale = scale
        self.files = list()
        #- nets to draw FLIGHTLINES for: the pins that belong together,
        #- boxed and joined, over the layout that may or may not join
        #- them. None draws none; a list names them.
        self.flightnets = list(flightnets or [])

    def startLib(self,name):
        #- START FROM NOTHING. svgcells/svgdeps are module globals, and
        #- a long-lived process -- the MCP server is one -- otherwise
        #- carries the previous design's cells into this one, where a
        #- name that exists in both resolves to the older drawing. The
        #- symptom is a render that disagrees with the same file
        #- rendered from a fresh process.
        svgcells.clear()
        svgdeps.clear()
        self.libname = name + "_svg"
        if(not path.isdir(self.libname)):
            os.mkdir(self.libname)

    def endLib(self):
        pass


    FLIGHT_COLOURS = ["#ff0000", "#00c000", "#ff00ff", "#0088ff",
                      "#ff8800", "#8800ff", "#00aaaa", "#aa0044"]

    def _drawFlightlines(self, cell):
        """Pins that share a net, from the CHILDREN's published ports.

        A cell's own instance ports are not in the .cic, so the honest
        source is each child cell's ports placed by the instance that
        holds it. That is exact for an assembly of finished blocks --
        which is where flightlines are wanted -- and it is why the
        grouping is by PORT NAME: at this level the block publishes the
        net's own name.
        """
        design = getattr(self, "design", None)
        bynet = {}
        for child in getattr(cell, "children", []) or []:
            if not (hasattr(child, "isInstance") and child.isInstance()):
                continue
            sub = (getattr(child, "layoutcell", None)
                   or getattr(child, "_cell_obj", None))
            if sub is None and design is not None:
                sub = design.cells.get(getattr(child, "cell", ""))
            if sub is None:
                continue
            for c in getattr(sub, "children", []) or []:
                if not (hasattr(c, "isPort") and c.isPort()):
                    continue
                r = c.get() if hasattr(c, "get") else None
                if r is None:
                    continue
                rr = r.getCopy()
                rr.translate(child.x1, child.y1)
                bynet.setdefault(getattr(c, "name", ""), []).append(rr)
        n = 0
        for net in self.flightnets:
            rects = bynet.get(net) or []
            if len(rects) < 2:
                continue
            self.svgcell.addFlight(rects,
                                   self.FLIGHT_COLOURS[n % len(self.FLIGHT_COLOURS)],
                                   net)
            n += 1

    def startCell(self,cell):
        file_name_cell = self.libname + os.path.sep + cell.name + ".svg"
        print("INFO: %s" % file_name_cell)
        self.files.append(file_name_cell)
        self.svgcell = SvgCell(file_name_cell,cell,self.scale,self.x,self.y,)


    def endCell(self,cell):
        if(self.svgcell is not None and self.flightnets):
            self._drawFlightlines(cell)
        if(self.svgcell is not None):
            self.svgcell.closeAndSave()
            self.svgcell = None
        with open(self.libname + ".html","w") as fo:

            fo.write("""
<html><head>
            <style>
img {
    max-width: 50%;
    max-height: 50%;
}
</style>
            </head><body>""")
            self.files.reverse()
            for f in self.files:
                fo.write("<div style='border:1'><h3>" + f + "</h3>")
                fo.write("</p><img src='%s'></img></div>"%f)
            fo.write("</body></html>")

    def printPort(self,p):
        pass

    def printRect(self,r):

        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return


        layer = self.rules.getValue("layers",r.layer)

        #- Don't print unecessary layers
        if("material" in layer):
            material = layer["material"]
            if(re.search("metalres|marker|implant",material)):
                return


        color = ""
        if("color" in layer):
            color = self.rules.colorTranslate(layer["color"])

        fill = ""
        if("fill" in layer):
            fill = self.rules.colorTranslate(layer["fill"])

        if(fill == "nofill" or color == ""):
            return

        self.svgcell.addRect(r,color,fill)

        
    def printReference(self,inst):
        if(not inst or inst.isEmpty()):
            return

        self.svgcell.addRef(inst)

        #p = inst.getCellPoint()
        #x1 = self.toMicron(p.x)
        #y1 = self.toMicron(p.y)

        #rotation = inst.angle
        #if(rotation == ""):
        #    rotation = "R0"
            

    def printText(self,t):
        if self.svgcell is None or t is None:
            return
        self.svgcell.addText(t)
