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
from ..core.cell import Cell
from ..core.port import Port
import sys
from os import path
import re
import numpy as np
import glob
import os


class XschemSymbol(Cell):
    def __init__(self,libname,cell,printer,symbolName):
        super().__init__()
        self.cell = cell
        self.libname = libname
        self.symbolName = symbolName

        self.symbol_from_lib = False
        symbol_to_use = ""
        if(symbolName != ""):
            for s in printer.lib_symbols:
                if(symbol_to_use):
                    continue
                base = os.path.basename(s)
                if(base == symbolName + ".sym"):
                    symbol_to_use = s
                elif(os.path.sep in symbolName and s.endswith(symbolName + ".sym")):
                    symbol_to_use = s


        self.ports = dict()
        print(symbol_to_use)
        if(symbol_to_use):
            self.read(symbol_to_use)

        self.updateBoundingRect()

        pass

    def read(self,filename):

    #TODO: Add Bounding box after reading ports
    #TODO: Figure out a way to inform on what is a "left,right,top,bottom" port. Could probably use the center of bounding box, and how the ports are
    #located compared to that

        self.symbuffer = list()
        self.symbol_from_lib = True

        if(not os.path.exists(filename)):
            raise Exception(f"Could not find symbol {filename}")


        with open(filename) as fi:
            for l in fi:
                if(l.startswith("v")): # Skip v line, I want to add more info
                    continue
                self.symbuffer.append(l)
                if(l.startswith("B")):

                    m = re.search("B\s+\d+\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+\{(.*)\}",l)


                    if(m is not None):
                        xb1 = float(m.group(1))
                        yb1 = float(m.group(2))
                        xb2 = float(m.group(3))
                        yb2 = float(m.group(4))

                        m1 = re.search("name=(\S+)",m.group(5))
                        if(m1 is None):
                            continue
                        name = m1.group(1)
                        r = Rect("PR",xb1,yb1,(xb2-xb1),(yb2-yb1))

                        p = Port(name, rect=r)
                        self.add(p)
                        m2 = re.search("dir=(\S+)",m.group(5))
                        if(m2 is None):
                            p.direction = "inputOutput"
                        else:
                            p.direction = m2.group(1)

                        self.ports[name] = p





    def getPin(self,x,y,name):

        x1 = x-20
        x2 = x
        xb1 = x1-2.5
        xb2 = x1+2.5
        yb1 = y-2.5
        yb2 = y + 2.5
        x3 = x2 + 5
        y3 = y - 5

        rect=Rect("PR",xb1,yb1,(xb2-xb1),(yb2-yb1))
        p = Port(name,rect=rect)
        
        self.add(p)

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
format="@name @pinlist @symname "
template="name=x1 "
} \n""")

        if(self.symbol_from_lib):
            for l in self.symbuffer:
                fsym.write(l)
        else:
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

            rbounds = Rect("PR",x1,y1,(x2-x1),(y2-y1))
            self.add(rbounds)

            self.updateBoundingRect()

            fsym.write(f"P 4 5 {x1} {y1} {x2} {y1} {x2} {y2} {x1} {y2} {x1} {y1} " + "{}\n")
            fsym.write("T {@symname} " + f" {x3} {y3}  0 0 0.25 0.25" + " {}\n")
            fsym.write("T {@name} " + f"0 -25 0 0 0.2 0.2 " + "{}\n")
        fsym.close()

class XschemPrinter(DesignPrinter):

    def __init__(self,filename,rules,smash=None):
        super().__init__(filename,rules)

        self.symbols = dict()

        self.current_cell = None

        self.smash = smash
        self.libpath =""
        self.xstep = 400
        self.ystep = 100
        self.xspace = 100
        self.ix1 = 300
        self.iy1 = 0
        self.ymax = 1000

        self.lib_symbols = list()
        for slib in self.rules.symbol_libs:

            path = os.path.expandvars(slib + os.path.sep + "*.sym")
            sym = glob.glob(path)
            for s in sym:
                self.lib_symbols.append(s)



    def startLib(self,name):


        self.libpath =  name
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

        sym = XschemSymbol(self.libpath,cell,self,cell.symbol)
        self.symbols[cell.name] = sym

        if("noSchematic" in cell.meta):
            #print(self.lib)
            sym.read(self.libname + "/" + cell.name + ".sym")
            sym.updateBoundingRect()
            return



        self.openCellFile(file_name_cell)


        header = """v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
"""
        self.fcell.write(header)

        y = 0
        counter = 0




        #- Will use the spice defition ports
        for node in cell.ckt.nodes:
            p = node
            pinName = p
            pinCommonName = re.sub(r"<|>|:","_",pinName)

            pinDirection = "inputOutput"
            if(p in sym.ports):
                pinDirection = sym.ports[p].direction

            if(pinDirection == "in"):
                self.fcell.write("C {devices/ipin.sym} " + f"0 {y} 0 0 " + "{" + f"name=p{counter} lab={p}" + "}\n")
            elif(pinDirection == "out"):
                self.fcell.write("C {devices/opin.sym} " + f"0 {y} 0 0 " + "{" + f"name=p{counter} lab={p}" + "}\n")
            else:
                self.fcell.write("C {devices/iopin.sym} " + f"0 {y} 0 0 " + "{" + f"name=p{counter} lab={p}" + "}\n")


            counter +=1
            y +=20



        sym.printSymbol()



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

        if("noSchematic" in c.meta):
            print(f" Skipping schematic for {c.name}")
            return

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


        #if(o.subcktName not in self.cells.keys()):
        #    print(f"Could not find instance {o.subcktName}")
        #    return

        _libname = ""
        if(o.isCktInstance()):
            instcell = self.cells[o.subcktName]
            _libname = os.path.basename(instcell.libpath)


        if(_libname == ""):
            _libname = self.libname



        dstr = "C {" + f"{_libname}/{o.subcktName}" + ".sym}" +  f" {self.ix1} {self.iy1}" + " 0 0 {name=" + f"X{o.name}" + "}\n"

        self.symbolAndWrite(dstr,o,o.subcktName)

    def symbolAndWrite(self,dstr,o,symbolName):

        self.fcell.write(dstr)

        if(o.isCktInstance()):
            instcell = self.cells[o.subcktName]
            intNodes = instcell.ckt.nodes
        else:
            #print(o.symnodes)
            intNodes = o.symnodes

        if(symbolName in self.symbols):
            instsym = self.symbols[symbolName]
        else:
            instsym = XschemSymbol(self.libpath,None,self,symbolName)
            if(not instsym.symbol_from_lib):
                raise Exception(f"Could not find symbol {symbolName}, are you missing a xschem lib reference in the techfile?")
            self.symbols[symbolName] = instsym

        #print(symbolName)
        #print(instsym.ports)


        nodes =  o.nodes


        
        if(len(nodes) != len(intNodes)):
            raise Exception(f"""Not the same number of nodes for instance and cell reference
      \tinstance {o.name}:\t{nodes}
      \tcell {instcell.ckt.name}:\t{intNodes}""")



        for z in range(len(nodes)):
            netName = nodes[z]
            portName = intNodes[z]

            if(portName not in instsym.ports):
                print(f"Could not find {portName} in {symbolName}")
                continue

            r = instsym.ports[portName].rect.getCopy()


            isRight = True
            if(r.centerX() < instsym.centerX()):
                isRight = False

            
            r.translate(self.ix1,self.iy1)

            xb2 = r.centerX()
            yb = r.centerY()


            rot = 0
            xb1 = xb2 - 20
            if(isRight):
                xb1 = xb2 + 20
                rot = 2

            #xb1 = xb2+80
            #if(portName == "B" and "Transistor" in instsym.cell.ckt.classname):
            #
            #else:
            #
            xlab = xb1

            self.fcell.write(f"N {xb1} {yb} {xb2} {yb} " + "{lab=" + netName + "}\n")

            self.fcell.write("C {devices/lab_pin.sym}" + f" {xlab} {yb} {rot} 0 " + "{name=l" + str(self.label_count) + " sig_type=std_logic lab=" + netName + " }\n")

            self.label_count +=1





        self.iy1 += instsym.height() + self.ystep
        self.iy1 = np.round(self.iy1/10)*10


        if(self.xstep  < instsym.width()):
            self.xstep = instsym.width() + self.xspace

        if(self.iy1 > self.ymax):
            self.ix1 += self.xstep + self.xspace
            self.iy1 = 0
        

        
        pass



    def printDevice(self,o):

        if("Mosfet" in o.classname):
            self.printMosfet(o)
        elif("Resistor" in o.classname):

            #- NF means in series for highres
            if("nf" in o.properties):
                nf = o.properties["nf"]

                n = o.nodes[0]
                p = o.nodes[1]
                b = o.nodes[2]

                myname = o.name

                for i in range(0,nf):
                    mynodes = [n,p,b]
                    if(i >= 0 and i < nf-1):
                        mynodes[1] = "INT_" + str(i)

                    if(i > 0 and i < nf):
                        mynodes[0] = "INT_" + str(i-1)

                    o.nodes = mynodes
                    o.name = myname + "_" + str(i)
                    self.printResistor(o)
                o.name = myname
                o.nodes = [n,p,b]



            else:
                self.printResistor(o)
        pass

    #- Only support sky130nm for now
    def printMosfet(self,o):

        try:
            odev = self.rules.device(o.deviceName)
        except Exception as e:
            raise(Exception("Could not find '" + o.deviceName + "' in rule file\n"))


        typename = odev["name"]
        o.symnodes = odev["ports"]



        dstr = """C {(sym).sym} (x1) (y1) 0 0 {name=(instName)
L=(length)
W=(width)
nf=(nf)
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'"
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'"
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=(model)
spiceprefix=X
}
"""

        tr = typename.split("__")
        model = tr[1]
        sym = typename.replace("__","/")


        dstr= dstr.replace("(sym)",sym) \
            .replace("(model)",model) \
            .replace("(nf)",str(o.properties["nf"])) \
            .replace("(length)",str(o.properties["length"])) \
            .replace("(width)",str(o.properties["width"]*o.properties["nf"])) \
            .replace("(instName)",o.name) \
            .replace("(x1)",str(self.ix1)) \
            .replace("(y1)",str(self.iy1))
            #.replace("(instName)")

        self.symbolAndWrite(dstr,o,sym)



    def printResistor(self,o):

        if(o.deviceName == "mres"):
            odev = self.rules.device(o.deviceName + o.properties["layer"])
        else:
            odev = self.rules.device(o.deviceName)

        typename = odev["name"]

        dstr = """C {(sym).sym} (x1) (y1) 0 0 {name=(instName)
W=(width)
L=(length)
model=(model)
mult=1}
"""

        tr = typename.split("__")
        model = tr[1]
        sym = typename.replace("__","/")

        o.symnodes = odev["ports"]
        port0 = odev["ports"][0]
        port1 = odev["ports"][1]

        #o.nodes[0] = port0
        #o.nodes[1] = port1


        dstr= dstr.replace("(sym)",sym) \
            .replace("(model)",model) \
            .replace("(length)",str(o.properties["length"])) \
            .replace("(width)",str(o.properties["width"])) \
            .replace("(instName)",o.name) \
            .replace("(x1)",str(self.ix1)) \
            .replace("(y1)",str(self.iy1))


        self.symbolAndWrite(dstr,o,sym)
