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

import sys
import os
import yaml
import re
import logging

class DesignPrinter():

    def __init__(self, filename,rules):
        self.filename = filename
        self.rules = rules
        self.cell = None
        self.cells = dict()
        self.f = None
        self.exclude = ""
        self.log = logging.getLogger("Printer")


    def openFile(self,name):
        self.f = open(name,"w")


    def closeFile(self):
        if(self.f):
            self.f.close()

    def printChildren(self,children):
        for child in children:
            if(not child): 
                continue
            if(child.isInstance() or child.isCut()):
                self.printReference(child)
            elif(child.isPort()):
                if(child.spicePort):
                    self.printPort(child)
            elif(child.isText()):
                self.printText(child)
            elif(child.isLayoutCell() or child.isCell()):
                self.printChildren(child.children)
            elif(child.isRect()):
                self.printRect(child)
            else:
                if(hasattr(child,"children")):
                    self.printChildren(child.children)
                else:
                    print("DesignPrinter: don't know what to do with " + str(child) + " " + child.name)



    def printCell(self,c):


        if(c.isEmpty()):
            return





        self.startCell(c)
        self.cell = c


        self.printChildren(c.children)

        self.endCell(c)
        self.cell = None

    def startLib(self,name):
        self.openFile(name)

    def endLib(self):
        self.closeFile()

    
    #- Emit a cell only after the cells it instantiates. A printer that
    #- writes each cell once and refers to it BY NAME afterwards -- the
    #- SVG one does -- silently drops an instance whose cell has not
    #- been written yet, and then the FILE ORDER decides what the
    #- picture contains. Printers that inline their geometry do not
    #- care, so this is opt-in.
    orderByDependency = False

    def _dependencyOrder(self, d, cells):
        """`cells`, reordered so a cell follows everything it holds.

        Measured on LELO_TEMP: `LELOTEMP_CCMP.cic` merges ahead of
        `LELOTEMP_CMP.cic` (it sorts first), so both comparators came
        out as empty boxes and the render read as a placement bug that
        was not there. A cycle is impossible in a layout hierarchy;
        if one appears the cell is left where it was rather than lost.
        """
        known = set(cells)
        order, done, active = [], set(), set()

        def refs(children, out):
            #- the same walk printChildren does, so the order covers
            #- exactly what gets drawn -- CUTS included: they are cells
            #- like any other, and leaving them out put four via cells
            #- back in the "no cell to draw" list
            for ch in (children or []):
                if not ch:
                    continue
                if ch.isInstance() or ch.isCut():
                    out.append(getattr(ch, "name", ""))
                elif hasattr(ch, "children"):
                    refs(ch.children, out)
            return out

        def visit(name):
            if name in done or name not in known or name in active:
                return
            active.add(name)
            for r in refs(getattr(d.getCell(name), "children", []), []):
                visit(r)
            active.discard(name)
            done.add(name)
            order.append(name)

        for c in cells:
            visit(c)
        return order

    def print(self, d,stopcell=""):


        self.design = d
        self.startLib(self.filename)
        skip = False
        cells = d.cellNames()
        if self.orderByDependency and stopcell == "":
            cells = self._dependencyOrder(d, cells)
        for c in cells:
            if(skip):
                continue


            cell = d.getCell(c)

            if(cell.abstract):
                continue


            #- Store cell for later, will need it
            self.cells[cell.name] = cell

            #- Skip cells that are in regex self.exclude
            if(self.exclude != "" and re.search(self.exclude,cell.name)):
                continue

            #print(c,cell.libcell,cell.isUsed)
            #if(cell.libcell and not cell.isUsed):
            #    continue



            if(cell):
                self.printCell(cell)

            if("" != stopcell and c == stopcell ):
                skip = true

        self.endLib()

