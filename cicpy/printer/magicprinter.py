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


class MagicPrinter(DesignPrinter):

    #- The magic unit is not micron, it's 0.01 micron, which is angstrom/100
    def toMicron(self,angstrom):
        return int((angstrom/100))
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)

    def startLib(self,name):

        self.libname = name
        if(not path.isdir(self.libname)):
            os.makedirs(self.libname)

    def endLib(self):

        pass

    def openCellFile(self,name):
        print(f"Writing {name}")
        self.fcell = open(name,"w")

    def closeCellFile(self):

        for layer in self.rects:
            self.fcell.write(self.rects[layer])

        for layer in self.cuts:
            r = self.cuts[layer]
            self.fcell.write(f"<< {layer} >>\nrect %d %d %d %d\n" % (self.toMicron(r.x1),self.toMicron(r.y1),self.toMicron(r.x2),self.toMicron(r.y2)))

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
        self.cuts = dict()
        self.portOrder = dict()
        self.properties = list()

        #- running number if cells don't have instance names
        self.xinst = 0


        #- Cut's need to be handled differently
        self.isCut = False

        self.labels.append("<< labels >>\n")

        file_name_cell = self.libname + os.path.sep + cell.name + ".mag"

        self.openCellFile(file_name_cell)

        if(cell.ckt is not None):
            for i in range(0,len(cell.ckt.nodes)):
                n = cell.ckt.nodes[i]
                self.portOrder[n] = i+1



        self.fcell.write("magic\n")
        self.fcell.write("tech " + self.rules.techlib + "\n")
        self.fcell.write("magscale 1 1\n")

        #- So adding timestamp for the exact time
        currentDate = datetime.date.today()

        self.fcell.write("timestamp %d\n" % time.mktime(currentDate.timetuple()))

        self.fcell.write("<< checkpaint >>\nrect %d %d %d %d\n"% (self.toMicron(cell.x1),self.toMicron(cell.y1),self.toMicron(cell.x2),self.toMicron(cell.y2)))

        if(cell.name.startswith("cut_")):
            self.isCut = True


    def endCell(self,cell):

        #- Print additional properties
        xu1 = self.toMicron(cell.x1)
        xu2 = self.toMicron(cell.x2)
        yu1 = self.toMicron(cell.y1)
        yu2 = self.toMicron(cell.y2)
        if(xu1 != xu2 and yu1 != yu2):
            self.properties.append("FIXED_BBOX %d %d %d %d" %( xu1,
                                                            yu1,
                                                            xu2,
                                                            yu2))
            pass
        else:
            print("Warning: Skip bounding box")

        self.closeCellFile()

        #- Write netlist
        if(cell.graph):
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
            print(self.portOrder)
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

        #- Handle cuts
        if(self.isCut and r.layer.startswith("VIA")):
            if(layerAlias not in self.cuts):
                self.cuts[layerAlias] = r

            ref = self.cuts[layerAlias]
            if(r.x1 < ref.x1):
                ref.x1 = r.x1
            if(r.x2 > ref.x2):
                ref.x2 = r.x2
            if(r.y1 < ref.y1):
                ref.y1 = r.y1
            if(r.y2 > ref.y2):
                ref.y2 = r.y2
            pass

        else:
            if(layerAlias not in self.rects):
                self.rects[layerAlias] = f"<< {layerAlias} >>\n"

            self.rects[layerAlias] += f"rect %d %d %d %d\n" % (self.toMicron(r.x1),self.toMicron(r.y1),self.toMicron(r.x2),self.toMicron(r.y2))

        
    def printReference(self,inst):

        if(not inst or inst.isEmpty()):
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




