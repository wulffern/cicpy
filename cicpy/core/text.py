from .rect import Rect

class Text(Rect):

    def __init__(self,name=""):
        super().__init__()
        self.name = name
        self.layer = "TXT"

    
    def fromJson(self,o):
        super().fromJson(o)
        self.name = o["name"]

    def toJson(self):
        o = super().toJson()
        o["class"] = "Text"
        o["name"] = self.name
        return o