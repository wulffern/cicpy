######################################################################
##        Copyright (c) 2021 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2021-8-4
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
import yaml
import re

class CellInfoPrinter(DesignPrinter):

    def __init__(self,filename,rules):
         super().__init__(filename,rules)
         self.data = dict()



    def startLib(self,name):
        self.openFile(name + ".yaml")

    def endLib(self):
        self.f.write(yaml.dump(self.data))
        self.closeFile()


    def startCell(self,cell):

        if(re.search("^.?[NP]CH|cut_",cell.name)):
            return

        self.c = dict()
        self.data[cell.name] = self.c
        self.c["ports"] = dict()
        self.c["portorder"] = list()
        for child in cell.children:
            if(child.isPort()):
                n = child.name
                self.c["ports"][child.name] = dict()

                direction = "inputOutput"
                tp = "analog"
                if(n in ["A","B","C","D"]):
                    direction = "input"
                    tp = "digital"

                if(n in ["Y","Q","QN"]):
                    direction = "output"
                    tp = "digital"


                if(n in ["AVDD","BULK_N","BULK_P"]):
                    tp = "power"
                    direction = "input"

                if(n in ["AVSS"]):
                    tp = "ground"
                    direction = "input"

                if("<" in n):
                    tp = "digital"


                self.c["ports"][child.name]["direction"] = direction
                self.c["ports"][child.name]["type"] = tp
                self.c["portorder"].append(child.name)
        self.c["function"] = ""


    def endCell(self,cell):

        pass

    def printRect(self,rect):
        pass

    def printPort(self,port):
        pass

    def printText(self,text):
        pass
    def printReference(self,inst):
        pass
