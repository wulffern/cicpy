from .cell import Cell
from .rect import Rect
from .rules import Rules

class RouteRing(Cell):

    def __init__(self, layer:str = None, name:str = None, rect:Rect = None, location:str = None, 
                 xgrid:int = None, ygrid:int = None, metalwidth:int = None):
        super().__init__()
        self.ignoreBoundaryRouting = False
        
        # Default constructor
        if layer is None:
            return


        # Adjust rectangle to get correct size
        if "b" in location:
            rect.adjust(0, -ygrid, 0, 0)
        if "t" in location:
            rect.adjust(0, 0, 0, ygrid)
        if "r" in location:
            rect.adjust(0, 0, xgrid, 0)
        if "l" in location:
            rect.adjust(-xgrid, 0, 0, 0)

        self.name = name

        x1 = rect.x1
        y1 = rect.y1
        x2 = rect.x2
        y2 = rect.y2

        self.bottom = Rect(layer, x1, y1, x2 - x1, metalwidth)
        self.left = Rect(layer, x1, y1, metalwidth, y2 - y1)
        self.right = Rect(layer, x2 - metalwidth, y1, metalwidth, y2 - y1)
        self.top = Rect(layer, x1, y2 - metalwidth, x2 - x1, metalwidth)

        if "b" in location:
            self.add(self.bottom)
            self.default_rectangle = self.bottom

        if "t" in location:
            self.add(self.top)
            self.default_rectangle = self.top

        if "l" in location:
            self.add(self.left)
            self.default_rectangle = self.left

        if "r" in location:
            self.add(self.right)
            self.default_rectangle = self.right

    def getDefault(self):
        """Get the default rectangle"""
        return self.default_rectangle

    def translate(self, dx: int, dy: int):
        """Translate the route ring by dx, dy"""
        Cell.translate(self, dx, dy)

    def moveTo(self, ax: int, ay: int):
        """Move the route ring to position ax, ay"""
        x1 = self.x1()
        y1 = self.y1()

        ax = ax - x1
        ay = ay - y1
        Cell.moveTo(self, ax, ay)

    def get(self, location: str):
        """Get a copy of the rectangle at the specified location"""
        # Handle multi-character location strings (e.g., "btrl", "rtbl")
        # Return the first matching side
        if "b" == location and hasattr(self, 'bottom') and self.bottom:
            return self.bottom.getCopy()
        elif "t" == location and hasattr(self, 'top') and self.top:
            return self.top.getCopy()
        elif "r" == location and hasattr(self, 'right') and self.right:
            return self.right.getCopy()
        elif "l" == location and hasattr(self, 'left') and self.left:
            return self.left.getCopy()
        
        # Fallback to exact matches
        if location == "bottom":
            return self.bottom.getCopy()
        elif location == "top":
            return self.top.getCopy()
        elif location == "right":
            return self.right.getCopy()
        elif location == "left":
            return self.left.getCopy()
        return None

    def getPointer(self, location: str):
        """Get a pointer to the rectangle at the specified location"""
        # Handle multi-character location strings (e.g., "btrl", "rtbl")
        # Return the first matching side
        if "b" == location and hasattr(self, 'bottom') and self.bottom:
            return self.bottom
        elif "t" == location and hasattr(self, 'top') and self.top:
            return self.top
        elif "r" == location and hasattr(self, 'right') and self.right:
            return self.right
        elif "l" == location and hasattr(self, 'left') and self.left:
            return self.left
        
        # Fallback to exact matches
        if location == "bottom":
            return self.bottom
        elif location == "top":
            return self.top
        elif location == "right":
            return self.right
        elif location == "left":
            return self.left
        else:
            print(f"Could not find location = {location} on {self.name()}. Use top,bottom,left,right")
            return None

    def trimRouteRing(self, location: str, whichEndToTrim: str):
        """Trim the route ring at the specified location and end"""
        cuts = self.getChildren("cIcCore::Route")
        bounds = Cell.calcBoundingRect(cuts)

        r = self.getPointer(location)
        if r is None:
            return
            
        if "l" in whichEndToTrim:
            r.setLeft(bounds.x1())

        if "t" in whichEndToTrim:
            r.setTop(bounds.y2())

        if "r" in whichEndToTrim:
            r.setRight(bounds.x2())

        if "b" in whichEndToTrim:
            r.setBottom(bounds.y1())



class ChannelRoute(RouteRing):
    """A RouteRing variant with one side: a full-width horizontal bar
    riding a routing-channel track.

    A ring surrounds the cell; a channel route lies across it -- on
    top of the nmos row, under the pmos row -- spanning the whole
    top-level cell so that any column can drop onto it. It registers
    like a ring (``rail_<net>``), so addPowerConnection stretches
    pins to it the same way, and it trims the same way: trim() pulls
    the bar back to the outermost connection actually made, so an
    unused stretch of track is returned to the channel.
    """

    def __init__(self, layer:str = None, name:str = None, x1:int = None,
                 x2:int = None, y:int = None, metalwidth:int = None):
        Cell.__init__(self)
        self.ignoreBoundaryRouting = False
        if layer is None:
            return
        self.name = name
        self.bar = Rect(layer, int(x1), int(y - metalwidth / 2),
                        int(x2 - x1), int(metalwidth))
        self.add(self.bar)
        self.bottom = self.bar
        self.top = self.bar
        self.left = self.bar
        self.right = self.bar
        self.default_rectangle = self.bar

    def trim(self, ends: str = "lr"):
        """Pull the bar back to the outermost connection.

        The connections are the children addPowerConnection (or any
        caller) added to this object; the bar keeps one metalwidth of
        enclosure past the outermost of them. With no connections the
        bar is left alone -- an untouched rail is a statement, an
        invisible one is a bug hunt.
        """
        conns = [c for c in self.children if c is not self.bar]
        if not conns:
            return
        x1 = min(c.x1 for c in conns)
        x2 = max(c.x2 for c in conns)
        margin = self.bar.height()
        if "l" in ends:
            self.bar.x1 = max(self.bar.x1, x1 - margin)
        if "r" in ends:
            self.bar.x2 = min(self.bar.x2, x2 + margin)
