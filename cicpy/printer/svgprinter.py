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
import os
import re


svgcells = dict()

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

    def addRef(self,inst):

        p = inst.getCellPoint()
        x = self.translate(p.x)
        y = self.translate(p.y)

        transform = f"translate({x},{y})"

        rotation = inst.angle
        if(rotation == "MY"):
            transform = transform + " scale(-1,1) "
        elif(rotation == ""):
            pass
        else:
            print(f"Rotation {rotation} not implemented yet")
        
        if(inst.name not in self.refs):
            gr = svgcells[inst.name]
            grg = svgwrite.container.Group(id=inst.name + "_inst",opacity=0)
            grg.add(gr)
            self.add(grg)
            self.refs[inst.name] = grg


        use = svgwrite.container.Use("#"+inst.name,transform=transform )
        self.gr.add(use)



class SvgPrinter(DesignPrinter):

    def __init__(self,filename,rules,scale,x,y):
        super().__init__(filename,rules)
        self.x = x
        self.y = y
        self.scale = scale
        self.files = list()

    def startLib(self,name):
        self.libname = name + "_svg"
        if(not path.isdir(self.libname)):
            os.mkdir(self.libname)

    def endLib(self):
        pass


    def startCell(self,cell):
        file_name_cell = self.libname + os.path.sep + cell.name + ".svg"
        print("INFO: %s" % file_name_cell)
        self.files.append(file_name_cell)
        self.svgcell = SvgCell(file_name_cell,cell,self.scale,self.x,self.y,)


    def endCell(self,cell):
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
        pass
        #x1 = self.toMicron(t.x1)
        #y1 = self.toMicron(t.y1)
        #layerNumber = self.rules.layerToNumber(t.layer)
        #dataType = self.rules.layerToDataType(t.layer)
