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
import re

class Port(Rect):

    def __init__(self,name="",routeLayer=None,rect=None):
        super().__init__()
        self.name = name
        self.routeLayer = routeLayer
        self.rect = rect
        self.spicePort = True
        self.net = ""
        self.pinLayer = routeLayer
        self.direction = "inputOutput"

        self.sigclass = "signal"

        if(re.search("VSS",self.name)):
            self.sigclass = "ground"
        elif(re.search("VDD",self.name)):
            self.sigclass = "power"

        if(rect):
            self.x1 = rect.x1
            self.x2 = rect.x2
            self.y1 = rect.y1
            self.y2 = rect.y2


    
    def fromJson(self,o):

        super().fromJson(o)
        self.name = o["name"]
        self.spicePort = o["spicePort"]
        self.pinLayer = o["pinLayer"]
    
    def toJson(self):
        o = super().toJson()
        o["class"] = "Port"
        o["name"] = self.name

        o["spicePort"] = self.spicePort
        return o
