from .designprinter import DesignPrinter
import re

skipcells = "^.?(N|P)CH"

class VerilogPrinter(DesignPrinter):
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.cell = None

    def startLib(self,name):
        self.openFile(name + ".v")

    def endLib(self):
        self.closeFile()

    def skipCell(self,cell):



        if(re.search(skipcells,cell.name)):
            return True

        if(cell.isCell()):
            return True

        if(cell.ckt is None):
            return True

        if(cell.meta is None):
            return True

        return False

    def startCell(self,cell):

        if self.skipCell(cell):
            return

        self.cell = cell
        nodes = cell.ckt.nodes
        strports = ",".join(nodes)
        self.f.write(f"""
//-------------------------------------------------------------
// {cell.name} {cell.__class__}
//-------------------------------------------------------------
module {cell.name}({strports});
""")


    def endCell(self,cell):
        if self.skipCell(cell):
            return

        if("verilog" not in cell.meta):
            for o in cell.ckt.instances:
                self.printInstance(o)
        else:
            v = cell.meta["verilog"]
            if(type(v) is list):
                for vv in v:
                    self.f.write(vv + "\n")
            else:
                self.f.write(v)

        self.cell = None

        self.f.write("endmodule\n")

    def printRect(self,rect):
        pass

    def printPort(self,port):

        if self.skipCell(self.cell):
            return

        direction = "input"
        vtype = "logic"

        pmeta = None
        if( "ports" in self.cell.meta and port.name in self.cell.meta["ports"] ):
            pmeta = self.cell.meta["ports"][port.name]
            if("direction" in pmeta):
                direction = pmeta["direction"]
            if("type" in pmeta):
                vtype = pmeta["type"]

        self.f.write(f"{direction} {vtype} {port.name};\n")

        if(pmeta and "verilog" in pmeta):
            self.f.write(pmeta["verilog"] +"\n")

    def printText(self,text):
        pass
    def printReference(self,ref):
        pass

    def printInstance(self,inst):

        if(re.search(skipcells,inst.subcktName)):
            return



        self.f.write(f"{inst.subcktName} {inst.name} (" + ",".join(inst.nodes) + ");\n")
        pass
