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
from os import path
import os


class MagicPrinter(DesignPrinter):

    def toMicron(self,angstrom):
        return (angstrom/100)*2
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.noPortRect = False



    def startLib(self,name):

        self.libname = name + os.path.sep + "/mag"
        if(not path.isdir(self.libname)):
            os.makedirs(self.libname)
        


    def endLib(self):
        pass


    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):


        for layer in self.rects:
            self.fcell.write(self.rects[layer])

        for ss in self.use:
            self.fcell.write(ss)

        for ss in self.labels:
            self.fcell.write(ss)

        self.fcell.write("<< end >>\n")

        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):
        self.rects = dict()
        self.use = list()
        self.labels = list()
        self.portIndex = 1
        self.labels.append("<< labels >>\n")

        file_name_cell = self.libname + os.path.sep + cell.name + ".mag"

        self.openCellFile(file_name_cell)
        
        self.fcell.write("magic\n")
        self.fcell.write("tech " + self.rules.techlib + "\n")
        self.fcell.write("magscale 1 2\n")

        d = datetime.datetime.now()
        self.fcell.write("timestamp %d\n" % time.mktime(d.timetuple()))




    def endCell(self,cell):

        self.closeCellFile()

        
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

        lbl = f"""flabel {routeLayerAlias} s %d %d %d %d 0 FreeSans 400 0 0 0 {p.name}
port %d nsew
""" % (x1,y1,x2,y2,self.portIndex)
        self.portIndex += 1
        self.labels.append(lbl)

    def printRect(self,r):

        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return

        layerAlias = self.rules.layerToAlias(r.layer)

        if(layerAlias == ""):
            print(r.layer + "\n")
            return

        x1 = self.toMicron(r.x1)
        x2 = self.toMicron(r.x2)
        y1 = self.toMicron(r.y1)
        y2 = self.toMicron(r.y2)

        layerNumber = self.rules.layerToNumber(r.layer)

        if(layerAlias not in self.rects):
            self.rects[layerAlias] = f"<< {layerAlias} >>\n"

        self.rects[layerAlias] += f"rect %d %d %d %d\n" %(x1,y1,x2,y2)

        
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



        use = f"""use {inst.name} {inst.instanceName}
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




