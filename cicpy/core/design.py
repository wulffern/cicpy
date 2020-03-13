
from .rect import Rect
from .cell import Cell
from .layoutcell import LayoutCell
import json

class Design():

    def __init__(self):
        self.cells = dict()
        self.cellnames = list()

    def fromJsonFile(self,fname):
        jobj = None
        with open(fname,"r") as f:
            jobj = json.load(f)
        for o in jobj["cells"]:
            c = LayoutCell()
            c.fromJson(o)  
            self.cells[c.name] = c
            self.cellnames.append(c.name)          
    
    def cellNames(self):
        return self.cellnames
    
    def getCell(self,name):
        return self.cells[name]



        
