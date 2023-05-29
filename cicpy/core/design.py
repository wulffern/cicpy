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

from .rect import Rect
from .cell import Cell
from .layoutcell import LayoutCell

import gzip
import json

class Design():

    def __init__(self):
        self.cells = dict()
        self.cellnames = list()
        self.jcells = dict()
        self.prefix = ""


    def fromJsonFile(self,fname):
        jobj = None

        if(fname.endswith(".gz")):
            with gzip.open(fname,"r") as f:
                jobj = json.load(f)
        else:
            with open(fname,"r") as f:
                jobj = json.load(f)

        if(jobj is None):
            raise Exception("Could not read %s, unrecognized format" % fname)

        for o in jobj["cells"]:
            if("class" in o):
                if(o["class"] == "cIcCore::Cell"):
                    c = LayoutCell()
                else:
                    c = LayoutCell()

            c.design = self
            c.fromJson(o)
            self.cells[c.name] = c
            self.jcells[c.name] = o
            self.cellnames.append(c.name)

    def add(self,c):
        self.cells[c.name] = c
        self.cellnames.append(c.name)

    def cellNames(self):
        return self.cellnames
    
    def getCell(self,name):
        return self.cells[name]



        
