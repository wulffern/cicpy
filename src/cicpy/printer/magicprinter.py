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
import numpy as np
import datetime
import time
import re
from os import path
import os
import logging

class MagicPrinter(DesignPrinter):

    def _bbox_with_margin(self, cell):
        x1 = cell.x1
        y1 = cell.y1
        x2 = cell.x2
        y2 = cell.y2
        margin = getattr(cell, "fixed_bbox_margin", None)
        if margin is None:
            return (x1, y1, x2, y2)
        if isinstance(margin, (int, float)):
            margin = [margin, margin, margin, margin]
        if len(margin) != 4:
            return (x1, y1, x2, y2)
        return (
            x1 - margin[0],
            y1 - margin[1],
            x2 + margin[2],
            y2 + margin[3],
        )


    def toMicron(self,angstrom):
        #- Snap to 5 nm grid
        return int(np.round(angstrom/50))
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.exclude = r"^cut_"

    def startLib(self,name):

        self.libname = name
        if(not path.isdir(self.libname)):
            os.makedirs(self.libname)

    def endLib(self):

        pass

    def openCellFile(self,name):
        log = logging.getLogger("MagicPrinter")
        log.info(f"Writing {name}")
        self.fcell = open(name,"w")

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

    def startCell(self,cell):


        self.rects = dict()
        self.use = list()
        self.labels = list()
        self.portOrder = dict()
        self.properties = list()

        #- running number if cells don't have instance names
        self.xinst = 0

        self.labels.append("<< labels >>\n")

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

        x1, y1, x2, y2 = self._bbox_with_margin(cell)
        self.fcell.write("<< checkpaint >>\nrect %d %d %d %d\n"% (self.toMicron(x1),self.toMicron(y1),self.toMicron(x2),self.toMicron(y2)))

    def endCell(self,cell):

        #- Print additional properties
        x1, y1, x2, y2 = self._bbox_with_margin(cell)
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
        
        x1 = self.toMicron(p.x1)
        y1 = self.toMicron(p.y1)
        x2 = self.toMicron(p.x2)
        y2 = self.toMicron(p.y2)
        routeLayerAlias = self.rules.layerToAlias(p.layer)

        if(p.name not in self.portOrder):
            raise(Exception(f"Could not find {p.name} in circuit nodes"))


        direction = "bidirectional"
        if(p.direction == "input"):
            direction = "input"
        elif(p.direction == "output"):
            direction = "output"

        sigclass = p.sigclass

        lbl = f"""flabel {routeLayerAlias} s %d %d %d %d 0 FreeSans 400 0 0 0 {p.name}
port %d nsew %s %s
""" % (x1,y1,x2,y2,self.portOrder[p.name],sigclass,direction)
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

        x1 = self.toMicron(p.x)
        y1 = self.toMicron(p.y)

        x2 = x1 + self.toMicron(inst.width())
        y2 = y1 + self.toMicron(inst.height())

        rotation = inst.angle

        tr1 = "1 0"
        tr2 = "0 1"
        if(rotation == "MY"):
            tr1 = "-1 0"

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
