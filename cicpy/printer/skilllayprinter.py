from .designprinter import DesignPrinter
import sys
from os import path
import os

class SkillLayPrinter(DesignPrinter):

    def __init__(self,filename):
        super().__init__(filename)
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

    def close(self):
        if(self.fcell):
            self.fcell.close()

    def startCell(self,cell):

        file_name_cell = self.libname + "/" + cell.name + ".il"

        self.f.write("load(\"" + file_name_cell + "\")\n")

        self.openCellFile(file_name_cell)
        self.fcell.write(self.libstr)
        self.fcell.write(";- Create cell " + cell.name +  "\n" + "(let (layout net fig )\n layout = dbOpenCellViewByType(gdssLibName \"" + cell.name  + "\" \"layout\" \"maskLayout\" \"w\")\n")



    def endCell(self,cell):

        pass

        
    def printPort(self,p):


        
        direction = "inputOutput"
        
        #- TODO: Add printing of pin 

        

    def printRect(self,r):
        pass

    def printReference(self,inst):
        pass

    def printPort(self,port):

        pass