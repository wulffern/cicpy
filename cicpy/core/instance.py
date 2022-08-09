######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-13
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

from .point import Point
from .cell import Cell

class Instance(Cell):

    def __init__(self):
        super().__init__()
        self.instanceName = ""
        self.cell = ""
        self.libpath = ""
        self.angle = ""
        self.xcell = 0
        self.ycell = 0

    
    def fromJson(self,o):
        super().fromJson(o)
        self.instanceName = o["instanceName"]
        self.angle = o["angle"]
        self.cell = o["cell"]
        if("libpath" in o):
            self.libpath = o["libpath"]
        self.xcell = o["xcell"]
        self.ycell = o["ycell"]

    def isLayoutCell(self):
        c = self.getCell(self.cell)

        if(c is not None):
            return c.isLayoutCell()
        return False

        

    def getCellPoint(self):
        p = Point(self.x1 + self.xcell, self.y1 + self.ycell)
        return p

    def __str__(self):
        return  super().__str__() + " instanceName=%s xcell=%d ycell=%d angle=%s" %(self.instanceName,self.xcell,self.ycell,self.angle)
