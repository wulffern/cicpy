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
import re

from .cktobject import CktObject
from .cktinstance import CktInstance
from .device import Device
class Subckt(CktObject):

    def __init__(self):
        super().__init__()
        self.devices = list()
        self.instances = list()

    def fromJson(self,o):
        super().fromJson(o)

        #- Override name to support prefix
        self.name = self.prefix + o["name"]

        for d in o["devices"]:
            dd = Device()
            dd.fromJson(d)
            self.devices.append(dd)
            pass

        for i in o["instances"]:
            ii = CktInstance()
            ii.prefix = self.prefix
            ii.fromJson(i)
            self.instances.append(ii)
            pass

    def toJson(self):
        o = super().toJson()


        o["devices"] = []
        for d in self.devices:
            o["devices"].append(d.toJson())
        o["instances"] = []
        for i in self.instances:
            o["instances"].append(i.toJson())
        return o

    def parse(self,lineNumber,sbuffer):

        #- Get name and nodes
        firstLine = sbuffer.pop(0)

        reSubcktName = "^\s*.subckt\s+(\S+)"



        m = re.search(reSubcktName,firstLine,flags=re.IGNORECASE)
        if(m):
            self.name = m.groups()[0]
            firstLine = re.sub(reSubcktName,"",firstLine,flags=re.IGNORECASE)

        firstline = firstLine.strip()

        #- Remove parameters
        reParam = "\s+(\S+)\s*=\s*(\S+)"
        firstLine = re.sub(reParam,"",firstLine)

        #- Find Nodes
        self.nodes = re.split("\s+",firstLine)

        #- Get instances
        instanceLineNumber = lineNumber + 1
        for line in sbuffer:

            if(re.search("^\s*$",line)):
                continue

            #- Figure out whether it's an instance or not
            #
            #
            #inst = SubcktInstance()
            print(line)
