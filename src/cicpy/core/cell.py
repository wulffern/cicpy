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

from .rect import *
from .port import Port
from .text import Text
import re
import cicspi as spi

class Cell(Rect):

    def toMicron(self,angstrom):
        return (angstrom/10)/1000.0

    def __init__ (self,name=""):
        super().__init__()
        self.subckt = None
        self.name = name
        self.allports = dict()
        self.allPortNames = list()
        self.ignoreBoundaryRouting = False
        self.physicalOnly = False
        self.abstract = False
        self.children  = list()
        self.ports = dict()
        self.routes = list()
        self.ckt = None
        self.design = None
        self.symbol = ""
        self.prefix = ""
        self.physicalOnly = False
        self.libCell = False
        self.isUsed = False
        self.libpath = ""
        self.has_pr = False
        self.meta = list()
        self.obj = False #- Original JSON obj
        self.named_rects = dict()


    #- -----------------------------------------------------------------
    #- The abstract view: what is in the way, at any depth
    #- -----------------------------------------------------------------

    def hiddenUses(self):
        """Cells this one places that `children` does not name.

        Empty for a cell whose hierarchy IS its children, which is most
        of them. A reader that keeps its hierarchy elsewhere -- the
        magic one keeps `use` records out of children, because children
        is what placement, bounding boxes, ports and both writers read
        -- says so here instead.

        Each entry is ``(cell, dx, dy, mirror_x, mirror_y)``.
        """
        return []

    def blockCell(self):
        """This cell as a block view: its conductors and what it places.

        Built once per cell and remembered on it. See
        `core/blockcell.py` -- the view is a CELL, with a
        BlockCellInstance per cell placed, so nothing is copied per
        instance and a device cell used forty times is held once.
        """
        from .blockcell import BlockCell
        return BlockCell.of(self)

    def flatMetal(self, used_only=False, hidden_only=False):
        """Every conductor below this cell, in this cell's own frame.

        The flat form of `blockCell()`, for a caller that wants a list
        rather than a walk. It answers "what would a route run into
        here" -- the question `tracks`, `blockers`, the maze router and
        the connectivity check all ask, and which none of them could
        ask through a cell that places other cells. Measured on
        LELO_TEMP_DIG: a JNWTR standard cell came back as its pins and
        its two M4 supply bars, because the M2 and M3 of its M1-M4 via
        stacks are inside the cells it uses.

        `used_only` leaves out the cell's own rects. `hidden_only`
        leaves out everything a caller walking `children` can already
        see, which is what the rect collector wants: it descends into
        instances itself, and would count them twice.
        """
        block = self.blockCell()
        if hidden_only:
            return block.rects(hidden_only=True)
        out = block.rects()
        if used_only:
            own = {id(r) for r in block.own}
            return [r for r in out if id(r) not in own]
        return out

    #- -----------------------------------------------------------------
    #- what is CLEAR, which is the other half of the same question
    #- -----------------------------------------------------------------

    def freeColumns(self, layer, span=None, minwidth=None, net=None):
        """The x spans nothing on `layer` crosses, over `span` in y.

        A route across a placed block needs a corridor, and a corridor
        is a MEASUREMENT of the block, not a number to be spelled in
        the pycell that routes over it: `inst.x1 + 40000` is this
        technology, this floorplan and this day, and it is wrong after
        any of them changes.

        Measured through the block view, so a block made of cells
        answers for what its children own -- which is the whole point,
        since the metal that blocks a lane is rarely the parent's.

        `span` is the (lo, hi) in y that has to be clear; the default
        is the whole cell, which asks for a corridor a full-height
        riser could use. `minwidth` defaults to what the technology
        itself asks for a wire with a space on each side, so what
        comes back is corridors something can actually be drawn in.

        `net` is the net that wants the corridor, and its OWN metal is
        not in its way: a riser that lands on its own rung is
        connected, not shorted. Asked net-blind, LELO_TEMP_DIG has no
        free M5 column at all -- RST_B's own rungs cross the block
        full width at two heights. Asked for RST_B, the column its
        port already sits in comes back free, which is the true
        answer and the one the route needs.
        """
        return self._free(layer, span, minwidth, vertical=True, net=net)

    def freeRows(self, layer, span=None, minwidth=None, net=None):
        """The y spans nothing on `layer` crosses, over `span` in x.

        `freeColumns` turned on its side -- for a leg that crosses a
        block east to west rather than a riser that crosses it up.
        """
        return self._free(layer, span, minwidth, vertical=False, net=net)

    def _free(self, layer, span, minwidth, vertical, net=None):
        from .rules import Rules
        rules = Rules.getInstance()
        if minwidth is None and rules is not None:
            minwidth = int(rules.get(layer, "width")) + \
                2 * int(rules.get(layer, "space"))
        minwidth = int(minwidth or 0)
        #- along = the axis the corridor runs in, across = the axis it
        #- is measured on. A vertical corridor runs in y and is a span
        #- in x.
        if vertical:
            lo, hi = int(self.x1), int(self.x2)
            keep = (lambda r: (int(r.y1), int(r.y2)))
            take = (lambda r: (int(r.x1), int(r.x2)))
            limit = (int(self.y1), int(self.y2))
        else:
            lo, hi = int(self.y1), int(self.y2)
            keep = (lambda r: (int(r.x1), int(r.x2)))
            take = (lambda r: (int(r.y1), int(r.y2)))
            limit = (int(self.x1), int(self.x2))
        s1, s2 = span if span else limit
        s1, s2 = int(min(s1, s2)), int(max(s1, s2))
        flat = [r for r in self.flatMetal()
                if getattr(r, "layer", "") == layer]

        #- WHAT BELONGS TO THE NET IS MORE THAN WHAT IS LABELLED WITH
        #- IT. A net's wires carry its name, but the PORT rect that
        #- publishes it and the via pads that sit on it carry none --
        #- the block view stamps a net on routed metal and on nothing
        #- else. Measured on LELO_TEMP_DIG: RST_B's own port and the
        #- three pads on its own rungs chopped RST_B's corridor to
        #- 1000 units, and the net was told there was no way down to
        #- its own pin.
        #-
        #- So an UNATTRIBUTED rect that overlaps the net's own metal
        #- on this layer is the net's. Overlapping two nets at once
        #- would be a short, so there is nothing to disambiguate.
        mine = []
        if net is not None:
            mine = [r for r in flat if getattr(r, "net", "") == net]
            p = self.getPort(net)
            for pr in ([p.get()] if p is not None and p.get() is not None
                       else []):
                if getattr(pr, "layer", "") == layer:
                    mine.append(pr)

        def isMine(r):
            if net is None:
                return False
            if getattr(r, "net", "") == net:
                return True
            if getattr(r, "net", ""):
                return False
            for m in mine:
                if not (int(r.x2) <= int(m.x1) or int(r.x1) >= int(m.x2)
                        or int(r.y2) <= int(m.y1) or int(r.y1) >= int(m.y2)):
                    return True
            return False

        used = []
        for r in flat:
            #- a net's own metal is not an obstacle to itself
            if isMine(r):
                continue
            a, b = keep(r)
            #- only what actually stands in the corridor's way: a rect
            #- that ends before the span starts is not in it
            if b <= s1 or a >= s2:
                continue
            used.append(take(r))
        used.sort()
        free, at = [], lo
        for a, b in used:
            if a - at >= minwidth:
                free.append((at, a))
            at = max(at, b)
        if hi - at >= minwidth:
            free.append((at, hi))
        return free

    def getPort(self,name:str):
        p = None

        if(name in self.ports):
            p = self.ports[name]
        return p

    # Find the first rectangle in this cell that uses layer
    def getRect(self,layer):
        for child in self.children:
            if(child is None):
                continue
            if(child.layer == layer):
                return child
        return None
    
    def setBoundaryIgnoreRouting(self, bir):
        """Set whether to ignore boundary routing when calculating bounding rect"""
        self.ignoreBoundaryRouting = bool(bir)
    
    def boundaryIgnoreRouting(self):
        """Get whether boundary routing is ignored"""
        return self.ignoreBoundaryRouting
    
    # Add a rectangle to the cell, hooks updated() of the child to updateBoundingRect
    def add(self, child):
        if(child == None):
            import logging
            log = logging.getLogger("Cell")
            log.error(f"Attempted to add None/Null rectangle to cell {self.name}")
            raise Exception("Null rectangle added")

        if(child.isPort() or child.isInstancePort()):
            self.ports[child.name] = child
            self.allPortNames.append(child.name)
            # Populate allports dict - each port name maps to a list of ports
            if child.name not in self.allports:
                self.allports[child.name] = []
            self.allports[child.name].append(child)


        if(not child in self.children):
            if(child.isRoute()):
                self.routes.append(child)
            child.parent = self
            self.children.append(child)
            child.connect(self.updateBoundingRect)

        self.updateBoundingRect()

    
    # Move this cell, and all children by dx and dy
    def translate(self, dx, dy):
        super().translate(dx,dy)
        for child in self.children:
            child.translate(dx,dy)
        self.updateBoundingRect()
        self.emit_updated()

    # Mirror this cell, and all children around ax
    def mirrorX(self,ax):
        super().mirrorX(ax)
        for child in self.children:
            child.mirrorX(ax)
        for _, port in self.ports.items():
            port.mirrorX(ax)
        self.updateBoundingRect()
        self.emit_updated()


    # Mirror this cell, and all children around ay
    def mirrorY(self,ay):
        super().mirrorY(ay)
        for child in self.children:
            child.mirrorY(ay)
        for _, port in self.ports.items():
            port.mirrorY(ay)
        self.updateBoundingRect()
        self.emit_updated
        

    # Move this cell, and all children to ax and ay
    def moveTo(self,ax, ay):
        x1 = self.x1
        y1 = self.y1
        super().moveTo(ax,ay)
        for child in self.children:
            child.translate(ax - x1, ay - y1)
        self.updateBoundingRect()
        self.emit_updated()

    # Center this cell, and all children on ax and ay
    def moveCenter(self,ax, ay):
        self.updateBoundingRect()
        xc1 = self.centerX()
        yc1 = self.centerY()
        dx = ax - xc1
        dy = ay - yc1
        self.translate(dx, dy)

    # Shortcut for adding ports
    def addPort(self, name, rect):
        if(rect is None):
            return None
        p = Port(name)
        p.set(rect)
        p.spicePort = self.isASpicePort(name)
        self.add(p)
        return p
        
    # Mirror this cell, and all children around horizontal center point (basically flip horizontal)
    def mirrorCenterX(self):
        self.mirrorX(self.centerY())
        pass
        
        
    def mirrorCenterY(self):
        self.mirrorY(self.centerX())
        pass

    def updateBoundingRect(self):
        r = self.calcBoundingRect()
        self.setRect(r)
        pass

    # Calculate the extent of this cell. Should be overriden by children
    def calcBoundingRect(self):
        x1 = INT_MAX
        y1 = INT_MAX
        x2 = INT_MIN
        y2 = INT_MIN

        if(len(self.children) == 0):
            x1 = y1 = x2 = y2 = 0


        for child in self.children:
            #- ignoreBoundaryRouting keeps routing out of the bounding
            #- box, so a ring drawn around the cell does not become part
            #- of the cell it rings.
            #-
            #- cIcCore::Cell::updateBoundingRect writes this as
            #-   (!cr->isInstance() || cr->isCut())
            #- because there every child is an instance or a route. Here
            #- a LayoutCell's children are CellGroups, so keeping only
            #- instances keeps nothing and the box comes out INT_MAX.
            #- Say what is meant instead: routing does not count.
            #- The port had not(isInstance()) or not(isCut()), true for
            #- every plain instance, which emptied the box either way
            if(self.ignoreBoundaryRouting and self._isBoundaryRouting(child)):
                continue
            #- see calcBoundingRectFromList: a child still at
            #- (0,0)-(0,0) is a placeholder, not geometry at the origin
            if(child.x1 == 0 and child.y1 == 0
               and child.x2 == 0 and child.y2 == 0):
                continue
            cx1 = child.x1
            cx2 = child.x2
            cy1 = child.y1
            cy2 = child.y2

            if(cx1 < x1):
                x1 = cx1
            if(cy1 < y1):
                y1 = cy1
            if(cx2 > x2):
                x2 = cx2
            if(cy2 > y2):
                y2 = cy2


        r = Rect()

        r.setPoint1(x1,y1)
        r.setPoint2(x2,y2)

        return r

    @staticmethod
    def _isBoundaryRouting(child):
        """Is this child routing rather than content?

        Routes, route rings and the cuts they place. Used by
        updateBoundingRect when ignoreBoundaryRouting is set.
        """
        if(child.isRoute() or child.isCut()):
            return True
        #- a route rect COPIED into a published subcell is routing too;
        #- as a plain Rect it inflated the box and shifted the
        #- published origin by the guard overhang
        if(getattr(child, "is_routing", False)):
            return True
        for base in (child.__class__,) + child.__class__.__mro__:
            if(base.__name__ == "RouteRing"):
                return True
        return False

    @staticmethod
    def calcBoundingRectFromList(children, ignoreBoundaryRouting=False):
        """Static method to calculate bounding rect from a list of rectangles"""
        x1 = INT_MAX
        y1 = INT_MAX
        x2 = INT_MIN
        y2 = INT_MIN

        if len(children) == 0:
            x1 = y1 = x2 = y2 = 0

        for cr in children:
            if ignoreBoundaryRouting and (not cr.isInstance() or cr.isCut()):
                continue

            #- A child that is still (0,0)-(0,0) is a PLACEHOLDER, not
            #- geometry at the origin. A Route is created empty and only
            #- gets its rects when route() runs, so any box taken while
            #- one is queued is dragged to the origin and stays there.
            #-
            #- Measured: moving stack pycells to before beforeRoute --
            #- where their routes can actually be drawn -- put five such
            #- Routes in a cell before its power rings were built, and
            #- the cell came out more than twice as wide, with the rails
            #- stretched across the empty space and resetOrigins unable
            #- to pull it back because something genuinely sat at x=0.
            if cr.x1 == 0 and cr.y1 == 0 and cr.x2 == 0 and cr.y2 == 0:
                continue

            cx1 = cr.x1
            cx2 = cr.x2
            cy1 = cr.y1
            cy2 = cr.y2

            if cx1 < x1:
                x1 = cx1
            if cy1 < y1:
                y1 = cy1
            if cx2 > x2:
                x2 = cx2
            if cy2 > y2:
                y2 = cy2

        r = Rect()
        r.setPoint1(x1, y1)
        r.setPoint2(x2, y2)
        return r

    def isEmpty(self):
        if(self.name == ""):
            return True
        return False
    

    #- Abstract methods
    def paint():
        pass

    def route():
        pass

    def place():
        pass


    def fromJson(self,o):
        super().fromJson(o)

        #- The cell box stored in the cic file is the abutment box the
        #- compiler placed the cell on, not the extent of the drawn geometry.
        #- Adding the children later recomputes x1..y2 from the drawing, so
        #- keep the stored box, it is what FIXED_BBOX and placement need
        if all(k in o for k in ("x1","y1","x2","y2")):
            self.cic_bbox = (o["x1"], o["y1"], o["x2"], o["y2"])

        self.prefix = self.design.prefix
        self.name = self.design.prefix  + o["name"]


        if("meta" in o and "symbol" in o["meta"]):
            self.symbol = o["meta"]["symbol"]
        else:
            self.symbol = self.name

        if("has_or" in o ):
            self.has_pr = o["has_pr"]

        if("libpath" in o ):
            self.libpath = o["libpath"]

        if("abstract" in o):
            self.abstract = o["abstract"]

        if("physicalOnly" in o):
            self.physicalOnly = o["physicalOnly"]

        if("libcell" in o):
            self.libcell = o["libcell"]

        if("cellused" in o):
            self.isUsed = o["cellused"]


        #- Handle subckt
        if("ckt" in o and isinstance(o["ckt"], dict) and len(o["ckt"]) > 0 and "name" in o["ckt"] and "nodes" in o["ckt"]):
            self.ckt = spi.Subckt()
            self.ckt.prefix = self.design.prefix
            self.ckt.fromJson(o["ckt"])


    def toJson(self):
        o = super().toJson()
        o["class"] = self.__class__.__name__

        if(o["class"] == "Cell"):
            o["class"] = "cIcCore::Cell"
        elif(o["class"] == "Layout"):
            o["class"] = "cIcCore::LayoutCell"

        o["name"] = self.name
        o["has_pr"] = self.has_pr

        ckt = self.ckt
        o["ckt"] = dict()
        if(ckt is not None):
            ockt = ckt.toJson()
            o["ckt"] = ockt

        oc = list()
        for child in self.children:
            oc.append(child.toJson())
        o["children"] = oc
        return o



    def __str__(self):
        return  super().__str__() + " name=%s " %(self.name)
        

    def toSkill(self):
        name  = "cw" + self.name
        ss = f"""
        {name} = makeTable("{name}" "")
        {name}["x"] = {self.toMicron(self.x1)}
        {name}["y"] = {self.toMicron(self.y1)}
        {name}["width"] = {self.toMicron(self.width())}
        {name}["height"] = {self.toMicron(self.height())}
        """
        return ss

    def getCell(self,cellname):
        if self.design and cellname in self.design.cells:
            return self.design.cells[cellname]
        return None

    def startswith(self,ss):
        if(self.name.startswith(self.prefix + ss)):
            return True
        return False

    def isASpicePort(self,name:str):
        if(self.subckt is None):
            return True
        if(name in self.subckt.nodes):
            return True
        else:
            return False

    def updatePort(self,name:str,r:Rect, routeLayer:str=None, pinLayer:str=None):
        p = None
        if(name in self.ports):
            p = self.ports[name]
            p.spicePort = self.isASpicePort(name)
            rr = r.getCopy(routeLayer) if (r is not None and routeLayer) else r
            p.set(rr)
            if routeLayer:
                p.routeLayer = routeLayer
            if pinLayer:
                p.pinLayer = pinLayer
        else:
            if(self.subckt):
                if(name in self.subckt.nodes):
                    rr = r.getCopy(routeLayer) if (r is not None and routeLayer) else r
                    p = Port(name, routeLayer=routeLayer, rect=rr)
                    p.spicePort = self.isASpicePort(name)
                    if pinLayer:
                        p.pinLayer = pinLayer
                    self.add(p)
        return p

    #     Port * getPort(QString name);
    #     Port * getCellPort(QString name);

    #     //! Get all ports on this cell
    #     QList<Port *>  ports();
    #     QMap<QString,QList<Port*>> allports();
    #     QList<QString> allPortNames();

    #     //! Update rectangle of port, if port does not exist a new one
    #     //! is created
    #     Port * updatePort(QString name,Rect* r);

    #     //! Spice subcircuit object
    #     cIcSpice::Subckt * subckt(){return _subckt;}
    #     cIcSpice::Subckt * setSubckt(cIcSpice::Subckt * val){ _subckt = val; return _subckt;}


    #     //! Get list of all children
    #     QList<Rect*> children(){return _children;}

    #     bool isASpicePort(QString name);
        

    #     //! Place children
    #     virtual void place();

    #     //! Route children
    #     virtual void route();

    #     //! Paint children, useful with a method after route
    #     virtual void paint();

    #     //! Automatically add remaing ports
    #     virtual void addAllPorts();

    #     //! Check if this cell contains a cell with name cell
    #     static bool hasCell(QString cell){
    #         return Cell::_allcells.contains(cell);
    #     }

    #     //! Get a named cell, returns empty cell if it does not exist, so you should check
    #     //! that the cell exists in this cell first
    #     static Cell* getCell(QString cell){
    #         if(Cell::_allcells.contains(cell)){
    #             return Cell::_allcells[cell];
    #         }else{
    #             Cell * c = new Cell();
    #             return c;
    #         }
    #     }

    #     //! Get a list of all cells in this design
    #     static QList<Cell*> getAllCells(){
    #         QList<Cell*> cells;
    #         foreach(Cell * cell,_allcells){
    #             cells.append(cell);
    #         }
    #         return cells;
    #     }

    #     //! Add a cell to the list of all cells
    #     static Cell* addCell(QString cell,Cell * c){
    #         Cell::_allcells[cell] = c;
    #         return c;
    #     }

    #     //! Add a cell, and use the cell->name() as key
    #     static Cell* addCell(Cell *c){
    #         Cell::_allcells[c->name()] = c;
    #         return c;
    #     }

  

    #     //! Find all rectangles by regular expression
    def findRectanglesByRegex(self, regex:str, layer:str):
        rects = list()
        self.findRectangles(rects, regex, layer)
        return rects

    def findRectangles(self, rects:list, name:str, layer:str):
        for child in self.children:
            if child is None:
                continue
            if layer and child.layer != layer:
                continue
            if re.search(name, getattr(child,'name', '')):
                rects.append(child)
            # Also include plain rects on layer when name matches empty or wildcard
            elif name == "" and (hasattr(child,'isRect') and child.isRect()):
                rects.append(child)

    def findAllRectangles(self, regex:str, layer:str):
        """Resolve ``regex`` to a list of rectangles on ``layer``.

        Mirrors ``cIcCore::Cell::findAllRectangles`` from ciccreator
        (`cic-core/src/core/cell.cpp:90-180`). The query string is
        comma-separated; each segment is one of:

        * ``"name"`` — matches this cell's local port named ``name``,
          this cell's ``named_rects[name]``, and any immediate
          child-instance port named ``name``.
        * ``"instname:path"`` — matches instances whose
          ``instanceName`` matches the regex ``instname`` and recurses
          into each match with ``path`` (which may itself contain
          further ``:`` segments).

        The layer argument filters: a rect is only returned when its
        layer equals ``layer`` (or ``layer`` is empty).
        """
        rects = []
        self._findRectanglesByRegex(rects, regex, layer)
        self._findRectangles(rects, regex, layer)
        return rects

    def _searchChildren(self):
        """Children that path-style searches (``findAllRectangles``) should
        traverse. Defaults to ``self.children``; ``LayoutCell`` overrides to
        flatten group-owned instances into the search space.
        """
        return list(self.children)

    def _findRectanglesByRegex(self, rects, regex, layer):
        for s in (s.strip() for s in (regex or "").split(",")):
            if not s:
                continue
            if ":" in s:
                inst_part, _, sub_path = s.partition(":")
                try:
                    inst_re = re.compile(inst_part)
                except re.error:
                    continue
                for child in self._searchChildren():
                    if child is None:
                        continue
                    if not (hasattr(child, "isInstance") and child.isInstance()):
                        continue
                    if not inst_re.search(getattr(child, "instanceName", "")):
                        continue
                    if hasattr(child, "_findRectanglesByRegex"):
                        child._findRectanglesByRegex(rects, sub_path, layer)
            else:
                # Local port lookup (exact name match — matches C++ behavior).
                port = self.ports.get(s)
                if port is not None:
                    rr = self._port_rect_on_layer(port, layer)
                    if rr is not None:
                        rects.append(rr)
                # named_rects entry by exact name.
                nr = self.named_rects.get(s)
                if nr is not None and (not layer or getattr(nr, "layer", "") == layer):
                    rects.append(nr)

    def _findRectangles(self, rects, name, layer):
        """Match `name` (no path semantics) against immediate child instance
        ports and named_rects on this cell. C++ counterpart:
        ``cIcCore::Cell::findRectangles``.
        """
        if not name or "," in name or ":" in name:
            return
        for child in self._searchChildren():
            if child is None:
                continue
            if not (hasattr(child, "isInstance") and child.isInstance()):
                continue
            for pi in getattr(child, "children", []):
                if pi is None:
                    continue
                if not (hasattr(pi, "isInstancePort") and pi.isInstancePort()):
                    continue
                if getattr(pi, "name", "") != name:
                    continue
                rr = self._port_rect_on_layer(pi, layer)
                if rr is not None:
                    rects.append(rr)
        nr = self.named_rects.get(name)
        if nr is not None and (not layer or getattr(nr, "layer", "") == layer):
            # Already appended in _findRectanglesByRegex when no `:`/`,`; skip
            # to avoid duplication.
            if nr not in rects:
                rects.append(nr)

    def _port_rect_on_layer(self, port, layer):
        if port is None or not hasattr(port, "get"):
            return None
        rr = port.get(layer)
        if rr is None:
            rr = port.get()
        if rr is None:
            return None
        if layer and getattr(rr, "layer", "") and getattr(rr, "layer", "") != layer:
            return None
        return rr

    #     QJsonObject toJson();
    #     void fromJson(QJsonObject o);
    #     QList<Rect*> getChildren(QString type);
        
    #     void addEnclosingLayers(QList<QString> layers);
        

    # protected:
    #     QList<Rect*> routes_;
    #     //! List of all cells
    #     static QMap<QString,Cell*> _allcells;

    #     //! Ports in this cell
    #     QMap<QString,Port*> ports_;

    #     QList<QString> allPortNames_;
        
    #     QMap<QString,QList<Port*>> allports_;

    #     //! Named Rects in this cell
    #     QMap<QString,Rect*> named_rects_;

    #     //! SPICE subcircuit related to this cell
    #     cIcSpice::Subckt * _subckt;

    #     //! Find bottom left rectangle in the cell
    #     Rect* getBottomLeftRect();
    #     //! Find top left rectangle in the cell
    #     Rect* getTopLeftRect();

    #     //! Children of this cell
    #     QList<Rect*> _children;
    #     QMap<QString,QList<Rect*>> children_by_type;
        

    # protected:
    #     QString instanceName_;
    #     bool boundaryIgnoreRouting_;
    #     bool _has_pr;        

    # private:
    #     //! Cell name
    #     QString _name;
    #     bool _physicalOnly;



    # signals:

    # public slots:
    #     void updateBoundingRect();
