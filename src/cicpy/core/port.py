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
        self.spicePort = True
        self.net = ""
        self.pinLayer = self._resolve_pin_layer(self.routeLayer)
        self.direction = "inputOutput"
        self.side = "left"

        self.sigclass = "signal"

        if(re.search("VSS",self.name)):
            self.sigclass = "ground"
        elif(re.search("VDD",self.name)):
            self.sigclass = "power"

        if(rect):
            self.set(rect)

    def set(self, rect):
        if rect is None:
            return
        self.rect = rect
        if getattr(rect, "layer", ""):
            self.routeLayer = rect.layer
            self.pinLayer = self._resolve_pin_layer(rect.layer)
        self.setRect(rect)


    
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
        r = None
        if(self.routeLayer):
            r = self.getCopy(layer)
            r.layer = self.routeLayer
            r.net = self.name
        return r
