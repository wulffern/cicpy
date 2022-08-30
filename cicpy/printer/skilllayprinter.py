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
from os import path
import os


class SkillLayPrinter(DesignPrinter):

    def toMicron(self,angstrom):
        return (angstrom/10)/1000.0
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.noPortRect = False


    def startLib(self,name):
        self.libpath = name + os.path.sep + "skill"
        if(not path.isdir(self.libpath)):
            os.makedirs(self.libpath)

        self.openFile(name + "_lay.il")

        self.froute = open(name + "_size.il","w")

        self.libstr = "gdssLibName = \"" + name + "\"\n pdkLib = \"" + name + "\"\n"
    
    def endLib(self):
        self.closeFile()
        self.froute.close()


    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):
        file_name_cell = self.libpath + os.path.sep + cell.name + "_lay.il"
        self.f.write("load(\"" + file_name_cell + "\")\n")

        self.froute.write(cell.toSkill())

        self.openCellFile(file_name_cell)
        
        self.fcell.write(self.libstr)
        self.fcell.write(";- Create cell " + cell.name +  "\n" + "(let (layout net fig )\n layout = dbOpenCellViewByType(gdssLibName \"" + cell.name  + "\" \"layout\" \"maskLayout\" \"w\")\n")


    def endCell(self,cell):
        self.fcell.write(" dbSave(layout) )\n")
        self.closeCellFile()

        
    def printPort(self,p):
        direction = "inputOutput"        
        
        x1 = self.toMicron(p.x1)
        y1 = self.toMicron(p.y1)
        x2 = self.toMicron(p.x2)
        y2 = self.toMicron(p.y2)
        layerNumber = self.rules.layerToNumber(p.pinLayer)
        dataType = self.rules.layerToDataType(p.pinLayer)

        routeLayerNumber = self.rules.layerToNumber(p.layer)
        routeDataType = self.rules.layerToDataType(p.layer)
        

        self.fcell.write(f"fig = dbCreateRect(layout list({routeLayerNumber} {routeDataType}) list({x1}:{y1} {x2}:{y2}))\n")

        self.fcell.write((f"net = dbCreateNet(layout \"{p.name}\")\n"
                         f"dbCreateTerm( net \"{p.name}\" \"{direction}\")\n"
                         "dbCreatePin(net fig)\n") )

        #- Scale font size of pin according to cell size
        w = self.toMicron(self.cell.width())
        l = self.toMicron(self.cell.width())
        wl = int((np.log2(w) + np.log2(l))/10) + 0.1


        self.fcell.write(f"dbCreateLabel(layout list({layerNumber} {dataType}) {x1}:{y1} \"{p.name}\" \"centerLeft\" \"R0\" \"stick\" {wl})\n")

        

    def printRect(self,r):

        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return

        layerNumber = self.rules.layerToNumber(r.layer)
        dataType = self.rules.layerToDataType(r.layer)

        x1 = self.toMicron(r.x1)
        x2 = self.toMicron(r.x2)
        y1 = self.toMicron(r.y1)
        y2 = self.toMicron(r.y2)
                
        
        self.fcell.write((f"fig = dbCreateRect(layout list({layerNumber} {dataType}"
                          f") list({x1}:{y1} {x2}:{y2}))\n"))
        
    def printReference(self,inst):
        if(not inst or inst.isEmpty()):
            return



        p = inst.getCellPoint()


        x1 = self.toMicron(p.x)
        y1 = self.toMicron(p.y)

        rotation = inst.angle
        if(rotation == ""):
            rotation = "R0"
            
        self.fcell.write( (
            f"mstr = dbOpenCellViewByType( pdkLib \"{inst.name}\" \"layout\")\n"
            f"layInst=dbCreateInst(layout mstr \"{inst.instanceName}\" {x1}:{y1} \"{rotation}\")\n"))


    def printText(self,t):

        x1 = self.toMicron(t.x1)
        y1 = self.toMicron(t.y1)
        layerNumber = self.rules.layerToNumber(t.layer)
        dataType = self.rules.layerToDataType(t.layer)

        self.fcell.write(f"dbCreateLabel(layout list({layerNumber} {dataType}) {x1}:{y1} \"{t.name}\" \"centerLeft\" \"R0\" \"stick\" 0.1)\n")
