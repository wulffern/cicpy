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

class DesignPrinter():

    def __init__(self, filename,rules):
        self.filename = filename
        self.rules = rules
        self.cell = None
        self.f = None

        self.info = None


    def loadInfoFile(self,finfo):

        #- Check if there is a cell info file
        if(os.path.exists(finfo)):
            with open(finfo,"r") as fi:
                self.info = yaml.safe_load(fi)

    def openFile(self,name):
        self.f = open(name,"w")


    def closeFile(self):
        if(self.f):
            self.f.close()

    def printChildren(self,children):
        for child in children:
            if(not child): 
                continue
            if(child.isInstance()):
                self.printReference(child)
            elif(child.isPort()):
                if(child.spicePort):
                    self.printPort(child)
            elif(child.isText()):
                self.printText(child)
            elif(child.isLayoutCell()):
                self.printChildren(child.children)

            elif(child.isRect()):
                self.printRect(child)
            else:
                print(str(child) + " " + child.name)



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

    
    def print(self, d,stopcell=""):
        self.design = d
        self.startLib(self.filename)
        skip = False
        cells = d.cellNames()
        for c in cells:
            if(skip):
                continue


            cell = d.getCell(c)

            if(cell.abstract):
                continue


            if(cell):
                self.printCell(cell)

            if("" != stopcell and c == stopcell ):
                skip = true

        self.endLib()

