from .rect import Rect

class Text(Rect):

    def __init__(self):
        super().__init__()
    
    def fromJson(self,o):
        super().fromJson(o)