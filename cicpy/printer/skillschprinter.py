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
import re
import os
class SkillSchPrinter(DesignPrinter):

    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.techfile = ""
        self.cells = dict()


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
        self.f.write(")")
        self.closeFile()

    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):
        file_name_cell = self.libname + "/" + cell.name + "_sch.il"

        #- Store cell for later, will need it
        self.cells[cell.name] = cell

        self.f.write("load(\"" + file_name_cell + "\")\n")

        self.openCellFile(file_name_cell)
        
        self.fcell.write(self.libstr)

        self.fcell.write(f"""
;Create cell
sch = dbOpenCellViewByType(schLibName "{cell.name}" "schematic" "schematic" "w")
schName = "{cell.name}"
xcoord = 1
ycoord = 0
        """)
        
        counter = 0
        x = 0
        y = 0

        #- Will use the spice defition ports
        #- TODO: Should it use Ports??
        for node in cell.ckt.nodes:
            p = node
            pinName = p
            pinCommonName = re.sub(r"<|>|:","_",pinName)
            pinDirection = "inputOutput"

            self.fcell.write(f"""
my{pinCommonName} = schCreatePin( sch {pinDirection}PinMaster "{pinName}" "{pinDirection}" nil {x}:{y} "R0" )
myTerm{pinCommonName} = (setof pin sch->terminals (pcreMatchp "{pinName}" pin->name))
myprebBox{pinCommonName} = car(car(my{pinCommonName}~>master~>terminals~>pins)~>fig~>bBox)
mybBox{pinCommonName} = dbTransformBBox(myprebBox{pinCommonName} my{pinCommonName}~>transform)
            """)

            counter +=1
            y +=0.2


        #- TODO: Could add symbols here

        #- Make symbol if it does not exist
        self.fcell.write("""
unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        """)


    def endCell(self,o):
        self.fcell.write("\nschCheck(sch)\ndbSave(sch)\n")

        pass

    def printCell(self,c):
        if(c.isEmpty()):
            return

        if(c.ckt is None):
            return
        
        self.startCell(c)

        for o in c.ckt.devices:
            self.printDevice(o)

        for o in c.ckt.instances:
            self.printInstance(o)

        self.endCell(c)


    def printDevice(self,o):


        print(o)
        pass

    def printInstance(self,o):

        x1 = "xcoord"
        y1 = "ycoord"
        rotation = "R270"

        if(o.subcktName not in self.cells.keys()):
            return

        instcell = self.cells[o.subcktName]
        
        ss = f"""
    ;;-------------------------------------------------------------------
    ;; Create instance {o.name}
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("{self.libname}" "{o.subcktName}" "symbol")
        schInst=dbCreateInst(sch schLib "{o.name}" {x1}:{y1} "{rotation}")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 1
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        """

        self.fcell.write(ss)

        nodes =  o.nodes
        intNodes = instcell.ckt.nodes

        
        if(len(nodes) != len(intNodes)):
            raise Exception(f"""Not the same number of nodes for instance and cell reference
      \tinstance {o.name}:\t{nodes}
      \tcell {instcell.ckt.name}:\t{intNodes}""")

        for z in range(len(nodes)):
            netName = nodes[z]
            portName = intNodes[z]

            ss = f"""
            signal = (setof sig schLib~>signals (member "{portName}" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "{netName}" "lowerLeft" "R0" "stick" 0.0625 nil )
            """

            self.fcell.write(ss)
            

        

        

        

        
        pass
    #def printRect(self,o):
    #    pass


    #def printText(self,o):
    #    pass

    #def printPort(self,o):
    #    pass

    #def printReference(self,o):
    #    pass
