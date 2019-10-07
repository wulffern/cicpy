from .cell import Cell

class Instance(Cell):

    def __init__(self):
        self.instanceName = ""
        self.cell = ""
        self.angle = ""
        self.xcell = 0
        self.ycell = 0
        super().__init__()
    
    def fromJson(self,o):
        super().fromJson(o)
        self.instanceName = o["instanceName"]
        self.cell = o["cell"]
        self.xcell = o["xcell"]
        self.ycell = o["ycell"]

