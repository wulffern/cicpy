from .rect import Rect

class Port(Rect):

    def __init__(self,name="",routeLayer=None,rect=None):
        super().__init__()
        self.name = name
        self.routeLayer = routeLayer
        self.rect = rect
        self.spicePort = True
        self.net = ""
        self.pinLayer = routeLayer
    
    def fromJson(self,o):

        super().fromJson(o)
        self.name = o["name"]
        self.spicePort = o["spicePort"]
        self.pinLayer = o["pinLayer"]
    
    def toJson(self):
        o = super().toJson()
        o["class"] = "Port"
        o["name"] = self.name

        o["spicePort"] = self.spicePort
        return o
