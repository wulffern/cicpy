from .cell import Cell
from .rect import Rect
from .rules import Rules


def strap_over(cell, r, layers, gaps=None):
    """Stack `r` with `layers`, stitched full length with cut arrays.

    `gaps` is [(lo, hi)] along the bar's long axis -- the spans to
    leave open. A ring row is also where a cell publishes its edge
    ports (measured on LELOTEMP_CCMPR: VC, RST and CMPO are M2 pads
    ON the ring rows, and a full-length M2 strap shorted all three),
    so the strap is laid as segments between the things that were
    there first. A cut ARRAY's intermediate metal is continuous, so
    gapping the cuts alone is not enough -- the metal is gapped too.
    """
    from .cut import Cut
    horizontal = (r.x2 - r.x1) >= (r.y2 - r.y1)
    lo, hi = (int(r.x1), int(r.x2)) if horizontal else (int(r.y1), int(r.y2))
    spans, at = [], lo
    for g1, g2 in sorted(gaps or []):
        if g1 > at:
            spans.append((at, min(g1, hi)))
        at = max(at, g2)
    if at < hi:
        spans.append((at, hi))
    #- THE STITCH IS CONTACT PAINT, NOT CUT INSTANCES. Magic fractures
    #- a contact rect into as many legal cuts as its own rules admit --
    #- which is the maximum-lowness stitch by definition -- and paint
    #- in the SAME cell merges with whatever cut a supply tie already
    #- landed on the ring. A Cut instance is a child cell, and two
    #- cells' contacts may not partially overlap: the array form cost
    #- 16 mcon/met1 errors where four ring legs' own cuts sat
    #- (measured on LELO_TEMP).
    rules = Rules.getInstance()
    out = []
    for a, b in spans:
        if horizontal:
            seg = Rect(r.layer, a, int(r.y1), b - a, int(r.y2 - r.y1))
        else:
            seg = Rect(r.layer, int(r.x1), a, int(r.x2 - r.x1), b - a)
        below = r.layer
        for lay in layers:
            sr = Rect(lay, seg.x1, seg.y1,
                      seg.x2 - seg.x1, seg.y2 - seg.y1)
            cell.add(sr)
            out.append(sr)
            #- the cut layer between the two metals, from the
            #- technology's own chain
            stack_layers = rules.getConnectStack(below, lay)
            cuts = [l.name for l in stack_layers
                    if "CUT" in str(getattr(l, "material", "")).upper()]
            for cname in cuts:
                #- Rules.get RAISES on a missing rule -- an `or 0`
                #- default never runs, and the first build died
                #- mid-write and deleted the .mag it was replacing.
                #- The cut layers here carry width/space but no
                #- enclosure rule, so the metal's own margin is used.
                try:
                    enc = int(rules.get(cname, "enclosure"))
                except Exception:
                    enc = 0
                enc = max(enc, 700)
                cr = Rect(cname, seg.x1 + enc, seg.y1 + enc,
                          (seg.x2 - seg.x1) - 2 * enc,
                          (seg.y2 - seg.y1) - 2 * enc)
                if cr.x2 > cr.x1 and cr.y2 > cr.y1:
                    cell.add(cr)
                    out.append(cr)
            below = lay
    return out


class RouteRing(Cell):

    #- class-level defaults: ChannelRoute constructs via Cell.__init__
    #- and never sets these, but inherits translate/_strapSides.
    straps = ()
    strap_gaps = {}

    def __init__(self, layer:str = None, name:str = None, rect:Rect = None, location:str = None,
                 xgrid:int = None, ygrid:int = None, metalwidth:int = None,
                 straps=None, strap_gaps=None):
        super().__init__()
        self.ignoreBoundaryRouting = False
        self.straps = list(straps or [])
        #- {side: [(lo, hi), ...]} in the cell's coordinates along the
        #- bar's long axis: the spans a strap must leave open. A ring
        #- row is also where a cell publishes its edge ports and where
        #- a parent's routes cross on the strap layer, so a SUBCELL's
        #- strap is legal only as segments between those spans -- see
        #- strap_over. Sides are "bottom"/"top"/"left"/"right".
        self.strap_gaps = dict(strap_gaps or {})
        
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

        self._strapSides()

    def _strapSides(self):
        """Copy every drawn side onto the strap layers, stitched full
        length with cut arrays.

        THE RING LAYER IS NOT A CONDUCTOR TO LEAN ON. These rings are
        laid on the pin layer, which in sky130 is LOCALI at ~12.8
        ohm/sq -- measured on LELO_TEMP, one 0.9 um side is 172
        squares, 2.2 kilo-ohm end to end, and that bar was the tile's
        entire supply spine. One met1 strap over it is 100x lower, and
        the stitch is not a tap every so often but a single cut array
        the LENGTH of the bar -- as many cuts as the cut layer's own
        width and space rules admit, which is what "as the technology
        dictates" means here. The strap is part of the ring, so
        wherever the ring is re-laid the strap re-lays with it.
        """
        self._clearStraps()
        if not self.straps:
            return
        for side in ("bottom", "top", "left", "right"):
            r = getattr(self, side, None)
            if r is None or r not in self.children:
                continue
            self._strap_rects += strap_over(self, r, self.straps,
                                            gaps=self.strap_gaps.get(side))

    def _clearStraps(self):
        for r in getattr(self, "_strap_rects", []):
            if r in self.children:
                self.children.remove(r)
        self._strap_rects = []

    def getDefault(self):
        """Get the default rectangle"""
        return self.default_rectangle

    def translate(self, dx: int, dy: int):
        """Translate the route ring by dx, dy.

        The straps are re-laid, not moved: their gap spans are
        declared in the CELL's coordinates (they mark where ports and
        parent crossings sit, which do not move when the ring is
        re-laid), so a strap baked at construction time and dragged
        along would carry its gaps away from the things they clear --
        measured on LELOTEMP_CMPR, whose recipe ring translates +4800
        after construction and every gap missed by exactly that.
        """
        self._clearStraps()
        Cell.translate(self, dx, dy)
        self._strapSides()

    def moveTo(self, ax: int, ay: int):
        """Move the route ring to position ax, ay"""
        self._clearStraps()
        x1 = self.x1()
        y1 = self.y1()

        ax = ax - x1
        ay = ay - y1
        Cell.moveTo(self, ax, ay)
        self._strapSides()

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
    """A RouteRing variant with one side: a bar riding a routing
    channel track.

    A ring surrounds the cell; a channel route lies across it,
    spanning the whole top-level cell so that anything along it can
    drop on. ``horizontal=True`` (the default) is the classic bar in
    the gap between rows: ``lo..hi`` is the x-range, ``coord`` the
    track's y. ``horizontal=False`` lays the bar ALONG a vertical
    channel -- a column gap -- with ``lo..hi`` the y-range and
    ``coord`` the track's x. It registers like a ring
    (``rail_<net>``), so addPowerConnection stretches pins to it the
    same way, and it trims the same way: trim() pulls the bar back
    to the outermost connection actually made, so an unused stretch
    of track is returned to the channel.
    """

    def __init__(self, layer:str = None, name:str = None, lo:int = None,
                 hi:int = None, coord:int = None, metalwidth:int = None,
                 horizontal:bool = True):
        Cell.__init__(self)
        self.ignoreBoundaryRouting = False
        self.horizontal = horizontal
        if layer is None:
            return
        self.name = name
        if horizontal:
            self.bar = Rect(layer, int(lo), int(coord - metalwidth / 2),
                            int(hi - lo), int(metalwidth))
        else:
            self.bar = Rect(layer, int(coord - metalwidth / 2), int(lo),
                            int(metalwidth), int(hi - lo))
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
        invisible one is a bug hunt. ``ends`` letters address the low
        end as ``l``/``b`` and the high end as ``r``/``t``, whatever
        the bar's direction.
        """
        conns = [c for c in self.children if c is not self.bar]
        if not conns:
            return
        horizontal = getattr(self, "horizontal",
                             self.bar.width() >= self.bar.height())
        if horizontal:
            lo = min(c.x1 for c in conns)
            hi = max(c.x2 for c in conns)
            margin = self.bar.height()
            if "l" in ends or "b" in ends:
                self.bar.x1 = max(self.bar.x1, lo - margin)
            if "r" in ends or "t" in ends:
                self.bar.x2 = min(self.bar.x2, hi + margin)
        else:
            lo = min(c.y1 for c in conns)
            hi = max(c.y2 for c in conns)
            margin = self.bar.width()
            if "l" in ends or "b" in ends:
                self.bar.y1 = max(self.bar.y1, lo - margin)
            if "r" in ends or "t" in ends:
                self.bar.y2 = min(self.bar.y2, hi + margin)
