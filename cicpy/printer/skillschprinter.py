######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-22
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
from os import path
import os
class SkillSchPrinter(DesignPrinter):

    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.techfile = ""


    def startLib(self,name):
        if(not path.isdir(name)):
            os.mkdir(name)
        
        self.openFile(name + "_sch.il")
        self.libname = name

        self.libstr = f"""schLibName = "{name}"
    techLib = "{self.techfile}"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")
"""

        self.f.write(f"""(let (schLibName techLib inputPinMasters outputPinMasters inputOutputPinMasters sch schName)
        {self.libstr}
""")
                     

    def endLib(self):
        self.closeFile()

    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):
        file_name_cell = self.libname + "/" + cell.name + "_sch.il"
        self.f.write("load(\"" + file_name_cell + "\")\n")

        self.openCellFile(file_name_cell)
        
        self.fcell.write(self.libstr)

    def endCell(self,o):
        pass

    def printCell(self,c):
        if(c.isEmpty()):
            return

        if(c.ckt is None):
            return
        
        self.startCell(c)

        self.printChildren(c.children)

        self.endCell(c)

    def printRect(self,o):
        pass


    def printText(self,o):
        pass

    def printPort(self,o):
        pass

    def printReference(self,o):
        pass



        
