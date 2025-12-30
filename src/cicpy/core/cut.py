######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-13
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

from .cell import Cell
from .rect import Rect
from .rules import Rules
from .layer import Layer
from .instancecut import InstanceCut
import logging

class Cut(Cell):
    
    # Static cache of Cut cells
    _cuts = {}

    def __init__(self, startlayer:str, stoplayer:str, hcuts:int, vcuts:int):
        super().__init__()
        self.log = logging.getLogger("Cut")
        self.startlayer = startlayer
        self.stoplayer = stoplayer
        self.hcuts = hcuts
        self.vcuts = vcuts
        
        rules = Rules.getInstance()
        layers = rules.getConnectStack(startlayer, stoplayer)
        
        if len(layers) == 0:
            self.log.debug(f"No layers to cut for {startlayer} {stoplayer}")
            return
        
        # Set the name
        self.name = self.makeName(layers[0].name, layers[-1].name, hcuts, vcuts)
        
        # Build the cut geometry
        for l in layers:
            if l.material in [Layer.metal, Layer.poly, Layer.diffusion]:
                # Metal/poly/diffusion layer
                encRule = l.next + "encOpposite"
                try:
                    encOpposite = rules.get(l.name, encRule)
                except:
                    encOpposite = 0
                    
                encThis = l.next + "enclosure"
                try:
                    if rules.hasRule(l.name, encRule):
                        enclosure = rules.get(l.name, encThis)
                    else:
                        enclosure = rules.get(l.name, "enclosure")
                except:
                    enclosure = 0
                
                try:
                    cut_width = rules.get(l.next, "width")
                    cut_height = rules.get(l.next, "height")
                    cut_space = rules.get(l.next, "space")
                except:
                    self.log.warning(f"Missing cut rules for {l.next}")
                    continue
                
                # Calculate rectangle dimensions
                if hcuts > vcuts:
                    r_width = encOpposite*2 + cut_width*hcuts + cut_space*(hcuts - 1)
                    r_height = enclosure*2 + cut_height*vcuts + cut_space*(vcuts - 1)
                elif hcuts == vcuts:
                    r_width = encOpposite*2 + cut_width*hcuts + cut_space*(hcuts - 1)
                    r_height = encOpposite*2 + cut_height*vcuts + cut_space*(vcuts - 1)
                else:
                    r_width = enclosure*2 + cut_width*hcuts + cut_space*(hcuts - 1)
                    r_height = encOpposite*2 + cut_height*vcuts + cut_space*(vcuts - 1)
                
                r = Rect(l.name, 0, 0, r_width, r_height)
                self.add(r)
                
            elif l.material == Layer.cut:
                # Cut layer
                encRule = l.name + "encOpposite"
                try:
                    encOpposite = rules.get(l.previous, encRule)
                except:
                    encOpposite = 0
                    
                encThis = l.name + "enclosure"
                try:
                    if rules.hasRule(l.previous, encRule):
                        enclosure = rules.get(l.previous, encThis)
                    else:
                        enclosure = rules.get(l.previous, "enclosure")
                except:
                    enclosure = 0
                
                try:
                    cut_width = rules.get(l.name, "width")
                    cut_height = rules.get(l.name, "height")
                    cut_space = rules.get(l.name, "space")
                except:
                    self.log.warning(f"Missing cut rules for {l.name}")
                    continue
                
                # Determine enclosure direction
                enc_x = encOpposite
                enc_y = enclosure
                if hcuts < vcuts:
                    enc_x = enclosure
                    enc_y = encOpposite
                elif hcuts == vcuts:
                    enc_x = encOpposite
                    enc_y = encOpposite
                
                # Create cut array
                xa1 = enc_x
                ya1 = enc_y
                for x in range(hcuts):
                    for y in range(vcuts):
                        r = Rect(l.name, xa1, ya1, cut_width, cut_height)
                        self.add(r)
                        ya1 += cut_height + cut_space
                    ya1 = enc_y
                    xa1 += cut_width + cut_space
        
        self.updateBoundingRect()

    @staticmethod
    def makeName(layer1:str, layer2:str, hcuts:int, vcuts:int):
        """Create a unique name for this cut configuration"""
        return f"cut_{layer1}{layer2}_{hcuts}x{vcuts}"

    @staticmethod
    def getInstance(startlayer:str, stoplayer:str, hcuts:int, vcuts:int):
        """Get or create a Cut instance with caching"""
        # No point in making a cut without layer transition
        if startlayer == stoplayer:
            return None
        
        tag1 = Cut.makeName(startlayer, stoplayer, hcuts, vcuts)
        tag2 = Cut.makeName(stoplayer, startlayer, hcuts, vcuts)
        
        # Check cache
        c = None
        if tag1 in Cut._cuts:
            c = Cut._cuts[tag1]
        elif tag2 in Cut._cuts:
            c = Cut._cuts[tag2]
        else:
            # Create new cut
            c = Cut(startlayer, stoplayer, hcuts, vcuts)
            if c.name:
                Cut._cuts[c.name] = c
        
        # Create instance
        if c and c.name:
            instance = InstanceCut()
            instance.setCell(c)
            instance.name = c.name
            instance.updateBoundingRect()
            return instance
        else:
            raise RuntimeError(f"Error: Could not create cut from {startlayer} to {stoplayer}")

    @staticmethod
    def getCutsForRects(routeLayer:str, rects:list, cuts:int, vcuts:int, leftAlignCut:bool=True):
        """Get cuts for a list of rectangles, matching C++ implementation"""
        cuts_out = []
        
        for r in rects:
            if r is None:
                continue
            
            if routeLayer != r.layer:
                # Need to create a cut
                inst = Cut.getInstance(routeLayer, r.layer, cuts, vcuts)
                
                if inst:
                    # Check if we need to swap cuts (orientation mismatch)
                    if (r.isVertical() and inst.isHorizontal()) or (r.isHorizontal() and inst.isVertical()):
                        # Got the wrong cut orientation, swap horizontal and vertical cuts
                        inst = Cut.getInstance(routeLayer, r.layer, vcuts, cuts)
                    
                    # Position the cut
                    if leftAlignCut:
                        inst.moveTo(r.x1, r.y1)
                    else:
                        inst.moveTo(r.x2 - inst.width(), r.y1)
                    
                    xc = r.centerX()
                    
                    # Resize rectangle if the center is not contained in the instance
                    if inst.x1 > xc or inst.x2 < xc:
                        r.setWidth(inst.width())
                    
                    cuts_out.append(inst)
        
        return cuts_out

    @staticmethod
    def getVerticalFillCutsForRects(layer1:str, rects:list, horizontal_cuts:int):
        """Get vertical fill cuts for rectangles (unimplemented)"""
        logging.getLogger("Cut").critical("Cut.getVerticalFillCutsForRects is unimplemented and will not generate fill cuts")
        cuts = []
        for r in rects:
            if r is None:
                continue
            if layer1 == r.layer:
                continue
        return cuts

    @staticmethod
    def getCuts():
        """Get all cached cuts"""
        return list(Cut._cuts.values())
