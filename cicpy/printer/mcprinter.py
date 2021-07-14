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

class MinMax():
    def __init__(self):
        self.max_x  = -1000000
        self.max_y = -10000000
        self.min_x = 10000000
        self.min_y = 10000000

    def updateMinMax(self,x1,x2,y1,y2):
        if(self.min_x > x1):
            self.min_x = x1
        if(self.max_x < x2):
            self.max_x = x2
        if(self.min_y > y1):
            self.min_y = y1
        if(self.max_y < y2):
            self.max_y = y2

    def toMine(self):
        return f"screen -x minecraft -X stuff '/forceload add {self.min_x} {self.min_y} {self.max_x} {self.max_y}\x0D'\n"

class MinecraftCuts(dict):

    def __init__(self,rules):
        self.rules = rules
        super().__init__()

    def addRect(self,r):
        coord_str = str(r.x1) + "," + str(r.y1)
        if(not (coord_str in self)):
                self[coord_str] = dict()
        self[coord_str][r.layer] = r

    def append(self,dd):

        for (key,v) in dd.items():
            if(key in self):
                for (kk,vv) in v.items():
                    self[key][kk] = vv
            else:
                self[key] = v

    def singleLayerCut(self,r):
        z1 = self.rules.layerToNumber(r.layer) + 5
        color = self.rules.layerToColor(r.layer)
        x1 = r.x1
        x2 = r.x2 -1
        y1 = r.y1
        y2 = r.y2 -1
        cmc_cmd = ""
        #cmc_cmd = f"/fill {x1} {z1+1} {y1} {x1+1} {z1+2} {y1+1} air replace\x0D"
        cmc_cmd += f"/setblock {x1} {z1} {y1} {color} replace\x0D"
        cmc_cmd += f"/setblock {x1} {z1+1} {y1} redstone_wire replace\x0D"
        cmc_cmd += f"/setblock {x1} {z1+1} {y1+1} {color} replace\x0D"
        cmc_cmd += f"/setblock {x1} {z1+2} {y1+1} redstone_wire replace\x0D"
        cmc_cmd += f"/setblock {x1} {z1+3} {y1+1} air replace\x0D"
        cmc_cmd += f"/setblock {x1+1} {z1+3} {y1+1} air replace\x0D"
        cmc_cmd += f"/setblock {x1+1} {z1+2} {y1+1} {color} replace\x0D"
        cmc_cmd += f"/setblock {x1+1} {z1+3} {y1+1} redstone_wire replace\x0D"
        #cmc_cmd += f"/setblock {x1+1} {z1+3} {y1} {color} replace\x0D"
        #cmc_cmd += f"/setblock {x1+1} {z1+4} {y1} redstone_wire replace\x0D"
        #cmc_cmd += f"/setblock {x1} {z1+3} {y1} {color} replace\x0D"
        #cmc_cmd += f"/setblock {x1} {z1+4} {y1} redstone_wire replace\x0D"
        c_cmd = f"screen -x minecraft -X stuff '{cmc_cmd}'\n"
        return c_cmd


    def print(self):
        buff = ""
        for (key,v) in self.items():
            for (kk,vv) in v.items():
                buff += self.singleLayerCut(vv)

        return buff


class MinecraftCellPrinter():

    def __init__(self,rules,design,c,x,y):
        self.rules = rules
        self.fcell = None
        self.design = design
        self.minmax = MinMax()
        self.buffer = ""
        self.x = x
        self.y = y
        self.c = c
        self.cuts = MinecraftCuts(self.rules)



    def translateToCellCoordinate(self,rect):
        r = rect.getCopy()
        r.translate(self.x,self.y)
        return r

    def printRect(self,r):
        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return

        if(not self.rules.hasLayer(r.layer)):
            return

        color = self.rules.layerToColor(r.layer)
        z1 = self.rules.layerToNumber(r.layer) + 5
        z2 = z1

        material = self.rules.getField("layers",r.layer,"material")


        r = self.translateToCellCoordinate(r)
        x1 = r.x1
        x2 = r.x2-1
        y1 = r.y1
        y2 = r.y2-1

        self.minmax.updateMinMax(x1,x2,y1,y2)

        mc_cmd = None

        #if(material in ["poly","metal","diffusion"] ):

        if(material in ["cut"]):
            self.cuts.addRect(r)

        elif(material in ["piston","torch"]):
            mc_cmd = f"/setblock {x1} {z2} {y1} {color}\x0D"
        else:
            mc_cmd = f"/fill {x1} {z1} {y1} {x2} {z2} {y2} {color} replace\x0D"
            if(material in ["metal","diffusion","poly"]):
                mc_cmd += f"/fill {x1} {z2+1} {y1} {x2} {z2+1} {y2} redstone_wire replace\x0D"

        if(mc_cmd):
            cmd = f"screen -x minecraft -X stuff '{mc_cmd}'\n"
            self.buffer += cmd


    def printReference(self,inst):
        p = inst.getCellPoint()

        x = p.x + self.x
        y = p.y + self.y

        cname = inst.cell

        if(cname.startswith("cut_")):
            cname = "mc_" + cname


        if(not cname in self.design.cells):
            print(f"Could not find cell {cname}")
            return


        child = self.design.cells[cname]


        mc = MinecraftCellPrinter(self.rules,self.design,child,x,y)
        buff = mc.print()
        self.cuts.append(mc.cuts)

        self.buffer +=  buff

    def clear(self):
        r =self.c.getCopy()
        r.translate(self.x,self.y)
        x1= r.x1
        x2= r.x2
        z1 = 5
        y1= r.y1
        y2= r.y2
        z2 = 20
        mc_cmd = f"/fill {x1} {z1} {y1} {x2} {20} {y2} air replace\x0D"
        return  f"screen -x minecraft -X stuff '{mc_cmd}'\n"


    def print(self):
        self.printChildren(self.c.children)
        return self.minmax.toMine() + self.buffer

    def printCuts(self):

        return self.cuts.print()

    def printChildren(self,children):
        for child in children:
            if(not child):
                continue
            if(child.isInstance()):
                self.printReference(child)
            elif(child.isPort()):
                pass
            elif(child.isText()):
                pass
            elif(child.isLayoutCell()):
                self.printChildren(child.children)
            elif(child.isRect()):
                self.printRect(child)
            else:
                print(str(child) + " " + child.name)
