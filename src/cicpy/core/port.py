######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-14
## ###################################################################
##  The MIT License (MIT)
## 
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
## 
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
## 
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##  
######################################################################

from .rect import Rect
from .rules import Rules
import re

class Port(Rect):

    @staticmethod
    def _resolve_pin_layer(route_layer):
        if not route_layer:
            return None
        rules = Rules.getInstance()
        if rules is None:
            return route_layer
        layer = rules.getLayer(route_layer)
        if layer is None:
            return route_layer
        return getattr(layer, "pin", route_layer) or route_layer

    def __init__(self,name="",routeLayer=None,rect=None):
        super().__init__()
        self.name = name

        self.routeLayer = routeLayer or (rect.layer if rect else None)
        self.rect = rect
        self.alternates = [rect] if rect is not None and getattr(rect, "layer", "") else []
        #- follow the rect from birth, exactly as set() does: a port
        #- built on a ring bar must move when the bar is trimmed
        if rect is not None:
            rect.connect(self.updateRect)
        self.spicePort = True
        self.net = ""
        self.pinLayer = self._resolve_pin_layer(self.routeLayer)
        self.direction = "inputOutput"
        self.side = "left"

        self.sigclass = "signal"

        from .mazerouter import supply_polarity
        self.sigclass = supply_polarity(self.name) or "signal"

        if(rect):
            self.set(rect)

    def set(self, rect):
        """Adopt `rect` as this port's shape, AND FOLLOW IT.

        The rect a port is given is not final. A pattern paints one
        cell of its grid at a time and merges each new rectangle into
        the one on its left, so the rect handed over at the port's own
        character keeps growing as the row continues: `wSw` publishes S
        on a rect that is two cells wide when set() runs and three by
        the end of the row.

        The C++ connects the rect's updated() signal to the port for
        exactly this reason. cicpy's Rect already emits to `listeners`
        on every edge move, so subscribe -- copying once leaves the
        port a cell short of the metal it names.
        """
        if rect is None:
            return
        #- a port REMEMBERS every rect it is given, one per layer: a
        #- transistor's gate is set once on PO and again on M1, and a
        #- route on either layer asks get(layer) for the right one.
        #- The C++ keeps the same list (alternates_rectangles_).
        if getattr(rect, "layer", ""):
            self.alternates = [r for r in getattr(self, "alternates", [])
                               if r.layer != rect.layer]
            self.alternates.append(rect)
            self.routeLayer = rect.layer
            self.pinLayer = self._resolve_pin_layer(rect.layer)
        #- Subscribe ONCE. The C++ returns early when handed the rect it
        #- already holds; do not copy that here. Plenty of cicpy code
        #- moves a rect by assigning x1/x2 straight, which emits nothing,
        #- and those callers rely on a later set() to refresh the port --
        #- so always re-read the geometry, and only guard the listener.
        if rect is not self.rect:
            self.rect = rect
            rect.connect(self.updateRect)
        self.setRect(rect)

    def mirrorY(self, ax):
        """A port does not mirror ITSELF -- it follows its rect.

        The rect is a child of the same cell and mirrors in the same
        sweep; letting the port mirror too applied the fold twice and
        put every mirrored cell's pins back on the unmirrored side.
        The C++ Port::mirrorY does exactly this: updateRect(), nothing
        else.
        """
        self.updateRect()

    def mirrorX(self, ay):
        self.updateRect()

    def updateRect(self):
        """The rect moved; take its geometry, but keep our own layer."""
        if self.rect is None:
            return
        self.x1 = self.rect.x1
        self.y1 = self.rect.y1
        self.x2 = self.rect.x2
        self.y2 = self.rect.y2


    
    def fromJson(self,o):

        super().fromJson(o)
        self.name = o["name"]
        self.spicePort = o.get("spicePort", True)
        self.routeLayer = self.layer
        self.pinLayer = o.get("pinLayer", self._resolve_pin_layer(self.layer))
        self.rect = self.getCopy(self.layer)
        self.rect.net = self.name
    
    def toJson(self):
        o = super().toJson()
        o["class"] = "Port"
        o["name"] = self.name

        o["spicePort"] = self.spicePort
        return o

    def get(self,layer=None):
        #- a copy of this port's rect: on `layer` if the port was
        #- ever set there, else on its route layer (C++ Port::get)
        if layer:
            for a in getattr(self, "alternates", []):
                if a.layer == layer:
                    rp = a.getCopy()
                    rp.net = self.name
                    return rp
        r = None
        if(self.routeLayer):
            r = self.getCopy(layer)
            r.layer = self.routeLayer
            r.net = self.name
        return r
