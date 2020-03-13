from .designprinter import DesignPrinter
import sys
from os import path
import os


class SkillLayPrinter(DesignPrinter):

    def toMicron(self,angstrom):
        return (angstrom/10)/1000.0
    
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.noPortRect = False



    def startLib(self,name):
        if(not path.isdir(name)):
            os.mkdir(name)
        
        self.openFile(name + ".il")
        self.libname = name
        self.libstr = "gdssLibName = \"" + name + "\"\n pdkLib = \"" + name + "\"\n"
    
    def endLib(self):
        self.closeFile()


    def openCellFile(self,name):
        self.fcell = open(name,"w")

    def closeCellFile(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):

        file_name_cell = self.libname + "/" + cell.name + ".il"

        self.f.write("load(\"" + file_name_cell + "\")\n")

        self.openCellFile(file_name_cell)
        self.fcell.write(self.libstr)
        self.fcell.write(";- Create cell " + cell.name +  "\n" + "(let (layout net fig )\n layout = dbOpenCellViewByType(gdssLibName \"" + cell.name  + "\" \"layout\" \"maskLayout\" \"w\")\n")



    def endCell(self,cell):
        self.fcell.write(" dbSave(layout) )\n")
        self.closeCellFile()

        
    def printPort(self,p):
        direction = "inputOutput"
        
        #- TODO: Add printing of pin

        self.fcell.write((f"net = dbCreateNet(layout \"{p.name}\")\n"
                         f"dbCreateTerm( net \"{p.name}\" \"{direction}\")\n"
                         "dbCreatePin(net fig)\n") )

        x1 = self.toMicron(p.x1)
        y1 = self.toMicron(p.y1)
        layerNumber = self.rules.layerToNumber(p.pinLayer)
        dataType = self.rules.layerToDataType(p.pinLayer)

        self.fcell.write(f"dbCreateLabel(layout list({layerNumber} {dataType}) {x1}:{y1} \"{p.name}\" \"centerLeft\" \"R0\" \"stick\" 0.1)\n")

        

    def printRect(self,r):

        #- Don't print lines
        if(r.x1 == r.x2 or r.y1 == r.y2):
            return

        #- Don't print empty layers
        if(r.layer == ""):
            return
        

        layerNumber = self.rules.layerToNumber(r.layer)
        dataType = self.rules.layerToDataType(r.layer)

        x1 = self.toMicron(r.x1)
        x2 = self.toMicron(r.x2)
        y1 = self.toMicron(r.y1)
        y2 = self.toMicron(r.y2)
                
        
        self.fcell.write((f"fig = dbCreateRect(layout list({layerNumber} {dataType}"
                          f") list({x1}:{y1} {x2}:{y2}))\n"))
        

    def printReference(self,inst):
        if(not inst or inst.isEmpty()):
            return

        p = inst.getCellPoint()
        x1 = self.toMicron(p.x)
        y1 = self.toMicron(p.y)

        rotation = inst.angle
        if(rotation == ""):
            rotation = "R0"
            
        self.fcell.write( (
            f"mstr = dbOpenCellViewByType( pdkLib \"{inst.name}\" \"layout\")\n"
            f"layInst=dbCreateInst(layout mstr \"{inst.instanceName}\" {x1}:{y1} \"{rotation}\")\n"))


    def printText(self,t):

        x1 = self.toMicron(t.x1)
        y1 = self.toMicron(t.y1)
        layerNumber = self.rules.layerToNumber(t.layer)
        dataType = self.rules.layerToDataType(t.layer)

        self.fcell.write(f"dbCreateLabel(layout list({layerNumber} {dataType}) {x1}:{y1} \"{t.name}\" \"centerLeft\" \"R0\" \"stick\" 0.1)\n")
