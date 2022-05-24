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
from ..core.rect import Rect
from ..core.port import Port
import sys
from os import path
import re
import os


class XschemSymbol(Rect):

    def __init__(self,libname,cell):
        self.cell = cell
        self.libname = libname

        self.x1 = 0
        self.x2 = 180
        self.y1 = 0
        self.y2 = 100
        self.ports = dict()

        pass

    def getPin(self,x,y,name):

        x1 = x-20
        x2 = x
        xb1 = x1-2.5
        xb2 = x1+2.5
        yb1 = y-2.5
        yb2 = y + 2.5
        x3 = x2 + 5
        y3 = y - 5

        p = Port(name, rect=Rect("PR",xb1,yb1,(xb2-xb1),(yb2-yb1)))
        self.ports[name] = p

        s = f"B 5 {xb1} {yb1}  {xb2} {yb2}" + " {name=" + f"{name}"+ " dir=inout }\n"
        s += f"L 4 {x1} {y} {x2} {y}" + " {}\n"
        s += "T {" + f"{name}" + "}" + f" {x3} {y3} 0 0 0.2 0.2 "  + " {}\n"

        return s

    def printSymbol(self):
        cell_sym = self.libname + os.path.sep + self.cell.name + ".sym"
        fsym = open(cell_sym,"w")
        fsym.write("v {xschem version=3.0.0 file_version=1.2 }\n")
        fsym.write("""K {type=subcircuit
format="@name @pinlist @symname"
template="name=x1"
} \n""")

        x = 0
        y = 0
        for node in self.cell.ckt.nodes:
            fsym.write(self.getPin(x,y,node))
            y += 20

        if(y == 0):
            y += 20
        x1 = x
        y1 = -10
        x2 = x1 + 180
        y2 = y - 10

        y3 = y1 + (y2 - y1)/2 - 10
        x3 = 50

        self.x1 = x1-40
        self.x2 = x2
        self.y1 = y1-10
        self.y2 = y2+10

        fsym.write(f"P 4 5 {x1} {y1} {x2} {y1} {x2} {y2} {x1} {y2} {x1} {y1} " + "{}\n")

        fsym.write("T {@symname} " + f" {x3} {y3}  0 0 0.25 0.25" + " {}\n")
        fsym.write("T {@name} " + f"0 -25 0 0 0.2 0.2 " + "{}\n")
        fsym.close()

class XschemPrinter(DesignPrinter):

    def __init__(self,filename,rules,smash=None):
        super().__init__(filename,rules)

        self.symbols = dict()
        self.cells = dict()
        self.current_cell = None

        self.smash = smash
        self.libpath =""
        self.xstep = 300
        self.ix1 = 300
        self.iy1 = 0
        self.ymax = 1000


    def startLib(self,name):

        self.libpath = "xschem" + os.path.sep + name
        self.libname =  name

        if(not path.isdir(self.libpath)):
            os.makedirs(self.libpath)

    def endLib(self):
        pass

    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):
        file_name_cell = self.libpath + os.path.sep + cell.name + ".sch"

        self.current_cell = cell
        self.ix1 = self.xstep
        self.iy1 = 0
        self.label_count = 0
        
        #- Store cell for later, will need it
        self.cells[cell.name] = cell

        self.openCellFile(file_name_cell)

        self.fcell.write("v {xschem version=3.0.0 file_version=1.2 }\n")

        y = 0
        counter = 0

        #- Will use the spice defition ports
        #- TODO: Should it use Ports??
        for node in cell.ckt.nodes:
            p = node
            pinName = p
            pinCommonName = re.sub(r"<|>|:","_",pinName)
            pinDirection = "inputOutput"

            self.fcell.write("C {devices/iopin.sym} " + f"0 {y} 0 0" + "{" + f"name=p{counter} lab={p}" + "}\n")

            counter +=1
            y +=20


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

        sym = XschemSymbol(self.libpath,cell)
        self.symbols[cell.name] = sym
        sym.printSymbol()


        #- Make symbol if it does not exist
        #self.fcell.write(f"""
        #syb =  ddGetObj("{sl}" "{short_name}" "symbol")
        #if( syb then
        #  syb_dd = dbOpenCellViewByType("{sl}" "{short_name}" "symbol")
        #  dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        #)


#unless( ddGetObj(schLibName schName "symbol")
#        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
#)
#        """)


    def endCell(self,o):
 #       self.fcell.write("\nschCheck(sch)\ndbSave(sch)\n")

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

        if(o.subcktName not in self.cells.keys()):
            return

        instcell = self.cells[o.subcktName]
        instsym = self.symbols[o.subcktName]

        self.fcell.write("C {" + f"{self.libname}/{o.subcktName}" + ".sym}" +  f" {self.ix1} {self.iy1}" + " 0 0 {name=" + f"{o.name}" + "}\n")




        nodes =  o.nodes
        intNodes = instcell.ckt.nodes

        
        if(len(nodes) != len(intNodes)):
            raise Exception(f"""Not the same number of nodes for instance and cell reference
      \tinstance {o.name}:\t{nodes}
      \tcell {instcell.ckt.name}:\t{intNodes}""")

        for z in range(len(nodes)):
            netName = nodes[z]
            portName = intNodes[z]

            r = instsym.ports[portName].rect.getCopy()

            r.translate(self.ix1,self.iy1)

            xb2 = r.centerX()
            yb = r.centerY()
            xb1 = xb2 - 40
            xlab = xb1

            self.fcell.write(f"N {xb1} {yb} {xb2} {yb}" + "{lab=" + netName + "}\n")

            self.fcell.write("C {devices/lab_pin.sym}" + f" {xlab} {yb} 0 0  " + "{name=l" + str(self.label_count) + " sig_type=std_logic lab=" + netName + " }\n")

            self.label_count +=1



            #print(netName, portName,r)



        self.iy1 += instsym.height()


        if(self.xstep + 100 < instsym.width()):
            self.xstep = instsym.width() + 100

        if(self.iy1 > self.ymax):
            self.ix1 += self.xstep
            self.iy1 = 0
        

        
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
        return


        if("Mosfet" in o.classname):
            self.printMosfet(o)
        elif("Resistor" in o.classname):
            self.printResistor(o)

        pass

    def printMosfet(self,o):
        return

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
        return

        try:
            odev = self.rules.device(o.deviceName + o.properties["layer"])
        except Exception as e:

            raise(Exception("Could not find '" + o.deviceName + o.properties["layer"]+ "' in rule file\n"))



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
