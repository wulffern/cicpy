
######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-21
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

from .cktobject import CktObject
class Device(CktObject):
    def __init__(self):
        super().__init__()
        self.deviceName = ""
        
    def fromJson(self,o):
        super().fromJson(o)
        self.deviceName = o["deviceName"]

    def toJson(self):
        o = super().toJson()
        o["deviceName"] = self.deviceName
        return o

    def __repr__(self):
        return super().__repr__() + ", deviceName = %s " %self.deviceName
