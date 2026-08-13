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
from ..core.gridcheck import GridChecker
import sys
import numpy as np
import datetime
import time
import re
from os import path
import os
import logging

class MagicPrinter(DesignPrinter):

    def _cell_bbox(self, cell):
        #- The abutment box the compiler stored in the cic file. The live
        #- x1..y2 are recomputed from the drawn children during load, which
        #- turns the box into a content extent and breaks the overlap tiling
        #- of stacked devices, so prefer the stored box
        bbox = getattr(cell, "cic_bbox", None)
        if bbox is not None:
            return bbox
        return (cell.x1, cell.y1, cell.x2, cell.y2)


    def toMicron(self,angstrom):
        #- Snap to 5 nm grid
        return int(np.round(angstrom/50))
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.exclude = r"^cut_"
        #- Every coordinate that leaves here must sit on the technology
        #- grid. See core/gridcheck.py
        self.gridcheck = GridChecker(rules,output="magic")

    def startLib(self,name):

        self.libname = name
        if(not path.isdir(self.libname)):
            os.makedirs(self.libname)

    def endLib(self):

        pass

    def openCellFile(self,name):
        """Open the cell's file -- BESIDE the real one, not over it.

        A cell is written a piece at a time, and anything that raises
        part way through (an off-grid coordinate is the usual one)
        used to leave a truncated .mag where a good one had been:
        90 bytes, no labels, and the next build reads it as the cell.
        The real name only appears when the whole cell is written.
        """
        log = logging.getLogger("MagicPrinter")
        log.info(f"Writing {name}")
        self.fcellname = name
        self.fcell = open(name + ".part","w")

    def _printFlattenedCutInstance(self, inst):
        if inst is None:
            return
        cell = getattr(inst, "layoutcell", None)
        if cell is None:
            cell = getattr(inst, "_cell_obj", None)
        if cell is None:
            return
        for child in cell.children:
            if child is None or not child.isRect():
                continue
            rr = child.getCopy()
            rr.translate(inst.x1, inst.y1)
            self.printRect(rr)

    def closeCellFile(self):

        for layer in self.rects:
            self.fcell.write(self.rects[layer])

        for ss in self.use:
            self.fcell.write(ss)

        for ss in self.labels:
            self.fcell.write(ss)

        self.fcell.write("<< properties >>\n")
        for ss in self.properties:
            self.fcell.write("string %s\n"%(ss))

        self.fcell.write("<< end >>\n")

        if(self.fcell):
            self.fcell.close()
            #- and NOW it is the cell
            name = getattr(self, "fcellname", "")
            if name:
                os.replace(name + ".part", name)

    def startCell(self,cell):


        self.rects = dict()
        self.use = list()
        self.labels = list()
        self.portOrder = dict()
        self.properties = list()

        #- running number if cells don't have instance names
        self.xinst = 0

        self.labels.append("<< labels >>\n")

        self.gridcheck.setCell(cell.name)

        file_name_cell = self.libname + os.path.sep + cell.name + ".mag"

        self.openCellFile(file_name_cell)

        if(cell.ckt is not None):
            for i in range(0,len(cell.ckt.nodes)):
                n = cell.ckt.nodes[i]
                self.portOrder[n] = i+1



        self.fcell.write("magic\n")
        self.fcell.write("tech " + self.rules.techlib + "\n")
        self.fcell.write("magscale 1 2\n")

        #- So adding timestamp for the exact time
        currentDate = datetime.date.today()

        self.fcell.write("timestamp %d\n" % time.mktime(currentDate.timetuple()))

        x1, y1, x2, y2 = self._cell_bbox(cell)
        self.gridcheck.check(x1,y1,x2,y2,layer="",net="",what="cell bounding box")
        self.fcell.write("<< checkpaint >>\nrect %d %d %d %d\n"% (self.toMicron(x1),self.toMicron(y1),self.toMicron(x2),self.toMicron(y2)))

    def endCell(self,cell):

        #- Print additional properties
        x1, y1, x2, y2 = self._cell_bbox(cell)
        xu1 = self.toMicron(x1)
        xu2 = self.toMicron(x2)
        yu1 = self.toMicron(y1)
        yu2 = self.toMicron(y2)
        if(xu1 != xu2 and yu1 != yu2):
            self.properties.append("FIXED_BBOX %d %d %d %d" %( xu1,
                                                            yu1,
                                                            xu2,
                                                            yu2))
            pass
        else:
            self.log.warning(" Skip bounding box")

        self.closeCellFile()

        #- Write netlist
        if(hasattr(cell,"graph") and cell.graph):
            with open(self.libname +  os.path.sep + cell.name + ".net","w") as fo:
                fo.write(" Netlist File\n")
                fo.write(" " + cell.name + "\n")
                for g in cell.graph:
                    fo.write(" " + g["node"] + "\n")
                    for i in g["instances"]:
                        fo.write(i["inst"] + "/" + i["node"] + "\n")
                    fo.write("\n")


        
    def printPort(self,p):
        layerAlias = self.rules.layerToAlias(p.layer)

        if(layerAlias == ""):
            return

        direction = "inputOutput"

        self.gridcheck.checkRect(p,what="port",where="name=" + str(p.name))

        x1 = self.toMicron(p.x1)
        y1 = self.toMicron(p.y1)
        x2 = self.toMicron(p.x2)
        y2 = self.toMicron(p.y2)
        routeLayerAlias = self.rules.layerToAlias(p.layer)

        direction = "bidirectional"
        if(p.direction == "input"):
            direction = "input"
        elif(p.direction == "output"):
            direction = "output"

        sigclass = p.sigclass

        lbl = f"""flabel {routeLayerAlias} s %d %d %d %d 0 FreeSans 400 0 0 0 {p.name}
""" % (x1,y1,x2,y2)

        #- Only a node on the subcircuit interface can be a port. A label on an
        #- internal net, such as the via addPortVias drops on a net between two
        #- child instances, gets the flabel without the port statement, so magic
        #- still names the net for LVS without inventing a pin.
        if(p.name in self.portOrder):
            lbl += "port %d nsew %s %s\n" % (self.portOrder[p.name],sigclass,direction)

        self.labels.append(lbl)

        self.printRect(p)

    def printRect(self,r):

        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return

        layerAlias = self.rules.layerToAlias(r.layer)

        if(layerAlias == ""):
            return

        layerNumber = self.rules.layerToNumber(r.layer)

        self.gridcheck.checkRect(r)

        if(layerAlias not in self.rects):
            self.rects[layerAlias] = f"<< {layerAlias} >>\n"

        self.rects[layerAlias] += f"rect %d %d %d %d\n" % (self.toMicron(r.x1),self.toMicron(r.y1),self.toMicron(r.x2),self.toMicron(r.y2))

        
    def printReference(self,inst):

        if(not inst or inst.isEmpty()):
            return

        if inst.isCut():
            self._printFlattenedCutInstance(inst)
            return



        p = inst.getCellPoint()

        self.gridcheck.check(p.x,p.y,p.x + inst.width(),p.y + inst.height(),
                             layer=inst.layer,net=inst.net,
                             what="instance " + str(inst.cell),
                             where="name=" + str(inst.instanceName))

        x1 = self.toMicron(p.x)
        y1 = self.toMicron(p.y)

        x2 = x1 + self.toMicron(inst.width())
        y2 = y1 + self.toMicron(inst.height())

        rotation = inst.angle

        #- Magic writes the transform as "a b c d e f", which maps a point in
        #- the child to (a*x + b*y + c, d*x + e*y + f). Only the 2x2 part is
        #- set here, c and f stay the placement point, since ciccreator has
        #- already folded the rotation offset into it through xcell/ycell.
        #- Anything not listed used to fall through to the identity, which
        #- placed rotated instances unrotated without saying so.
        orientations = {
            ""     : ("1 0",  "0 1"),
            "R0"   : ("1 0",  "0 1"),
            "MY"   : ("-1 0", "0 1"),
            "MX"   : ("1 0",  "0 -1"),
            "R90"  : ("0 -1", "1 0"),
            "R180" : ("-1 0", "0 -1"),
            "R270" : ("0 1",  "-1 0"),
        }

        if(rotation in orientations):
            tr1, tr2 = orientations[rotation]
        else:
            tr1, tr2 = orientations[""]
            print(f"Warning: orientation {rotation} of {inst.cell} is not known, placing it unrotated")

        path = ""
        if(inst.libpath != ""):
            path = "../" + os.path.basename(inst.libpath)
            #path = inst.cell


        instname = inst.instanceName
        if(instname is None or instname == ""):
            instname = "xcut" + str(self.xinst)
            self.xinst +=1

        use = f"""use {inst.cell} {instname} {path}
transform %s %d %s %d
box %d %d %d %d
""" %(tr1,x1,tr2,y1,x1,y1,x2,y2)
        self.use.append(use)


    def printText(self,t):
        return
        x1 = self.toMicron(t.x1)
        y1 = self.toMicron(t.y1)
        layerAlias = self.rules.layerToAlias(t.layer)

        if(layerAlias == ""):
            return
