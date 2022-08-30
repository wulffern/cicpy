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

    def __init__(self,filename,rules,smash=None):
        super().__init__(filename,rules)

        self.techfile = rules.getValue("technology","techlib")
        self.cells = dict()
        self.current_cell = None
        self.smash = smash


    def startLib(self,name):
        self.libname = name
        self.libpath = name + os.path.sep + "skill"
        if(not path.isdir(self.libpath)):
            os.makedirs(self.libpath)
        #if(not path.isdir(name)):
        #    os.mkdir(name)
        
        self.openFile(name + "_sch.il")

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
        file_name_cell = self.libpath + os.path.sep + cell.name + "_sch.il"

        self.current_cell = cell
        
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

        sl = self.rules.symbol_lib

        short_name = re.sub("(X\d+)*(_CV|_EV)?","",cell.name)

        if(cell.name.startswith("PCH")):
            short_name = "PCH"
        if(cell.name.startswith("CPCH")):
            short_name = "CPCH"
        if(cell.name.startswith("NCH")):
            short_name = "NCH"
        if(cell.name.startswith("CNCH")):
            short_name = "CNCH"
        #- Make symbol if it does not exist
        self.fcell.write(f"""
        syb =  ddGetObj("{sl}" "{short_name}" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("{sl}" "{short_name}" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        """)


    def endCell(self,o):
        self.fcell.write("\nschCheck(sch)\ndbSave(sch)\n")

        self.current_cell = None

        pass

    def printCell(self,c):
        if(c.isEmpty()):
            return

        if(c.ckt is None):
            return
        
        self.startCell(c)

        #- Hack to suport multi finger devices
        if(self.smash and re.search(self.smash,c.name)):

            #- Assume only transistors can be smashed, and assume everything is the same
            nf = len(c.ckt.instances)
            instcell = self.cells[c.ckt.instances[0].subcktName]
            mos = instcell.ckt.devices[0]
            mos.properties["nf"] = nf
            self.printDevice(mos)

        else:
             try:
                 for o in c.ckt.devices:
                     self.printDevice(o)

                 for o in c.ckt.instances:
                     self.printInstance(o)

             except Exception as e:
                 self.current_cell.ckt.printToJson()

                 raise(e)
        self.endCell(c)


    def printInstance(self,o):

        x1 = "xcoord"
        y1 = "ycoord"
        rotation = "R180"

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
                    xcoord = 2
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

    


    def printDevice(self,o):


        if("Mosfet" in o.classname):
            self.printMosfet(o)
        elif("Resistor" in o.classname and len(o.nodes)==3):
            self.printHighResistor(o)
        elif("Resistor" in o.classname):
            self.printResistor(o)

        pass

    def printMosfet(self,o):

        try:
            odev = self.rules.device(o.deviceName)
        except Exception as e:

            raise(Exception("Could not find '" + o.deviceName + "' in rule file\n"))


        typename = odev["name"]

        
        port0 = odev["ports"][0]
        port1 = odev["ports"][1]
        port2 = odev["ports"][2]
        port3 = odev["ports"][3]

        x1 = "xcoord"
        y1 = "ycoord"

        
        rotation = 0
        deviceCounter = 0

        ss = f"""
    ;;-------------------------------------------------------------------
    ;; Create transistor {o.name}
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType(techLib "{typename}" "symbol")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        ndrain = (setof sig schLib~>signals (member "{port0}" sig~>sigNames))
        ngate  = (setof sig schLib~>signals (member "{port1}" sig~>sigNames))
        nsource = (setof sig schLib~>signals (member "{port2}" sig~>sigNames))
        nbulk = (setof sig schLib~>signals (member "{port3}" sig~>sigNames))

        bBoxDrain = car(car(ndrain~>pins)~>fig)~>bBox
        bBoxSource = car(car(nsource~>pins)~>fig)~>bBox
        bBoxBulk = car(car(nbulk~>pins)~>fig)~>bBox
        bBoxGate = car(car(ngate~>pins)~>fig)~>bBox

        schInst=dbCreateInst(sch schLib "{o.name}_{deviceCounter}" {x1}:{y1} "{rotation}")
        """

        props = list()
        if("propertymap" in odev):
            #print(odev["propertymap"])
            ddict = dict()

            #- Go through propertymap and find all parameters
            for key in odev["propertymap"]:
                ddict[key] = dict()
                ddict[key]["val"] = o.properties[odev["propertymap"][key]["name"]]
                ddict[key]["str"] = odev["propertymap"][key]["str"]

            #- If a parameter is used in a string, then replace it
            for key in ddict:
                m = re.search("({\w+})",ddict[key]["str"])
                if(m):
                    for mg in m.groups():
                        rkey = re.sub("{|}","",mg)
                        if(rkey in ddict):
                            ddict[key]["str"] = re.sub(mg,str(ddict[rkey]["val"]),ddict[key]["str"])

                
            #- Write the properties
            for key in odev["propertymap"]:
                val = str(ddict[key]["val"]) + ddict[key]["str"]
                ss += f"""dbReplaceProp(schInst "{key}" 'string "{val}")\n"""
                props.append(key)



        ssprop = " ".join(map(lambda x: "\"%s\"" %x, props))

        
        ss += f"""
        (CCSinvokeInstCdfCallbacks schInst ?order list({ssprop}))

        ;;- Create wires
        pinDrain=dbTransformBBox(bBoxDrain schInst~>transform)
        pinSource=dbTransformBBox(bBoxSource schInst~>transform)
        pinGate=dbTransformBBox(bBoxGate schInst~>transform)
        pinBulk=dbTransformBBox(bBoxBulk schInst~>transform)

        """


        for (name,con) in zip(["D","G","S","B"],o.nodes):
            ss += f"bDest{name} = mybBox{con}\n"

        ss += """
        schCreateWire( sch "route" "flight" list(centerBox(pinDrain) centerBox(bDestD)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinSource) centerBox(bDestS)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinGate) centerBox(bDestG)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinBulk) centerBox(bDestB)) 0.0625 0.0625 0.0 )
        """

        self.fcell.write(ss)

        #print("Mosfet " + str(o))
        pass

    def printResistor(self,o):

        try:
            odev = self.rules.device(o.deviceName + o.properties["layer"])
        except Exception as e:
            print(o.deviceName+"\n")
            print(o.deviceName+"\n")
            print(e)
            raise(e)
            #raise(Exception("Could not find '" + o.deviceName + o.properties["layer"]+ "' in rule file\n"))



#        print(o)
#        print(odev)

        typename = odev["name"]


        port0 = odev["ports"][0]
        port1 = odev["ports"][1]
        

        x1 = "xcoord"
        y1 = "ycoord"

#        print(port0 + " " + port1)

        rotation = 0
        deviceCounter = 0

        ss = f"""

        ;;-------------------------------------------------------------------
        ;; Create Metal capacitor (two metal resistors) {o.name}
        ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType(techLib "{typename}" "symbol")

        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1

        schInst=dbCreateInst(sch schLib "{o.name}_a_{deviceCounter}" {x1}:{y1} "{rotation}")


    
        """

        props = list()
        if("propertymap" in odev):
            #print(odev["propertymap"])
            for key in odev["propertymap"]:
                val = str(o.properties[odev["propertymap"][key]["name"]]) + odev["propertymap"][key]["str"]
                ss += f"""dbReplaceProp(schInst "{key}" 'string "{val}")\n"""
                props.append(key)


        ssprop = " ".join(map(lambda x: "\"%s\"" %x, props))


        #- TODO: Fix this, right now this is not correct, the resistor should not connect to the pins, that's wrong.
        #raise("Hell")



        ss += f"""
        (CCSinvokeInstCdfCallbacks schInst ?order list({ssprop}))"""
        
        #- Resistor should only have two nodes
        if(len(o.nodes) != 2):
            raise ("Hell")

        for z in range(2):
            deviceport = odev["ports"][z]
            netName = o.nodes[z]
            ss += f"""
            deviceportn = (setof sig schLib~>signals (member "{deviceport}" sig~>sigNames))
            bBoxDport = car(car(deviceportn~>pins)~>fig)~>bBox
            pinDport=dbTransformBBox(bBoxDport schInst~>transform)
            wireId = schCreateWire( sch "draw" "full" list(centerBox(pinDport) rodAddToX(centerBox(pinDport) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pinDport) 0.125)  "{netName}" "lowerLeft" "R0" "stick" 0.0625 nil )
            """

        #if(o.nodes[0] in self.current_cell.ckt.nodes):
        #    pinCommonName = re.sub(r"<|>|:","_",o.nodes[0])
        #    ss += f"""
        #    bDestA = mybBox{pinCommonName};
        #    schCreateWire( sch "route" "flight" list(centerBox(pinAn) centerBox(bDestA)) 0.0625 0.0625 0.0 )
        #    """
        #if(o.nodes[1] in self.current_cell.ckt.nodes):
        #    pinCommonName = re.sub(r"<|>|:","_",o.nodes[1])
        #    ss += f"""
        #    bDestB = mybBox{pinCommonName};
        #    schCreateWire( sch "route" "flight" list(centerBox(pinBp) centerBox(bDestB)) 0.0625 0.0625 0.0 )
        #    """

        self.fcell.write(ss)
        #print("Resistors " + str(o))
     #   print(o)
        pass

    def printHighResistor(self,o):

        try:
            odev = self.rules.device(o.deviceName)
        except Exception as e:
            print(o.deviceName+"\n")
            print(e)
            raise(e)

        print(odev)

        typename = odev["name"]

        port0 = odev["ports"][0]
        port1 = odev["ports"][1]
        port2 = odev["ports"][2]

        x1 = "xcoord"
        y1 = "ycoord"

        rotation = 0
        deviceCounter = 0

        ss = f"""

        ;;-------------------------------------------------------------------
        ;; Create Metal capacitor (two metal resistors) {o.name}
        ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType(techLib "{typename}" "symbol")

        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1

        schInst=dbCreateInst(sch schLib "{o.name}_a_{deviceCounter}" {x1}:{y1} "{rotation}")



        """

        props = list()
        if("propertymap" in odev):
            #print(odev["propertymap"])
            for key in odev["propertymap"]:
                val = str(o.properties[odev["propertymap"][key]["name"]]) + odev["propertymap"][key]["str"]
                ss += f"""dbReplaceProp(schInst "{key}" 'string "{val}")\n"""
                props.append(key)


        ssprop = " ".join(map(lambda x: "\"%s\"" %x, props))


        #- TODO: Fix this, right now this is not correct, the resistor should not connect to the pins, that's wrong.
        #raise("Hell")



        ss += f"""
        (CCSinvokeInstCdfCallbacks schInst ?order list({ssprop}))"""

        #- HighResistor should have three nodes
        if(len(o.nodes) != 3):
            raise ("Hell")

        for z in range(3):
            deviceport = odev["ports"][z]
            netName = o.nodes[z]
            ss += f"""
            deviceportn = (setof sig schLib~>signals (member "{deviceport}" sig~>sigNames))
            bBoxDport = car(car(deviceportn~>pins)~>fig)~>bBox
            pinDport=dbTransformBBox(bBoxDport schInst~>transform)
            wireId = schCreateWire( sch "draw" "full" list(centerBox(pinDport) rodAddToX(centerBox(pinDport) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pinDport) 0.125)  "{netName}" "lowerLeft" "R0" "stick" 0.0625 nil )
            """

        #if(o.nodes[0] in self.current_cell.ckt.nodes):
        #    pinCommonName = re.sub(r"<|>|:","_",o.nodes[0])
        #    ss += f"""
        #    bDestA = mybBox{pinCommonName};
        #    schCreateWire( sch "route" "flight" list(centerBox(pinAn) centerBox(bDestA)) 0.0625 0.0625 0.0 )
        #    """
        #if(o.nodes[1] in self.current_cell.ckt.nodes):
        #    pinCommonName = re.sub(r"<|>|:","_",o.nodes[1])
        #    ss += f"""
        #    bDestB = mybBox{pinCommonName};
        #    schCreateWire( sch "route" "flight" list(centerBox(pinBp) centerBox(bDestB)) 0.0625 0.0625 0.0 )
        #    """

        self.fcell.write(ss)
        #print("Resistors " + str(o))
     #   print(o)
        pass
