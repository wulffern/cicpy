from .rect import Rect

class Port(Rect):

    def __init__(self):
        super().__init__()
    
    def fromJson(self,o):
        super().fromJson(o)