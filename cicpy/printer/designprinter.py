
import sys

class DesignPrinter():

    def __init__(self, filename,rules):
        self.filename = filename
        self.rules = rules
        

    def openFile(self,name):
        self.f = open(name,"w")


    def closeFile(self):
        if(self.f):
            self.f.close()

    def printChildren(self,children):
        for child in children:
            if(not child): 
                continue
            if(child.isInstance()):
                self.printReference(child)
            elif(child.isPort()):
                if(child.spicePort):
                    self.printPort(child)
            elif(child.isText()):
                self.printText(child)
            elif(child.isLayoutCell()):
                self.printChildren(child.children)

            elif(child.isRect()):
                self.printRect(child)
            else:
                print(str(child) + " " + child.name)



    def printCell(self,c):
        if(c.isEmpty()):
            return
        
        self.startCell(c)

        self.printChildren(c.children)

        self.endCell(c)

    def startLib(self,name):
        self.openFile(name)

    def endLib(self):
        self.closeFile()

    
    def print(self, d,stopcell=""):
        self.startLib(self.filename)
        skip = False
        cells = d.cellNames()
        for c in cells:
            if(skip):
                continue

            cell = d.getCell(c)

            if(cell):
                self.printCell(cell)

            if("" != stopcell and c == stopcell ):
                skip = true

        self.endLib()

