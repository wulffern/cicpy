#!/usr/bin/env python3
"""PatternTile -- a cell drawn from a character grid.

An object file gives PatternTile a picture of the cell: one string per
row, one character per column, first string is the TOP row.

    ["PO", "XXXXXXX",
           "X-----X",
           "XXXXXXX"]

`fillCoordinatesFromString` reads the picture into a coordinate grid;
`paint` walks the grid and turns each marked coordinate into geometry
on a pitch taken from the technology rules. The character says what to
draw:

    X x     a rectangle filling the cell of the grid
    G       a poly gate, sized to the minimum gate length
    m w     a rectangle at the layer's minimum length / width
    V       a rectangle spanning into the rows above and below
    3       three columns wide, at the layer's rule height
    c C     a contact to the next layer up (C offset half a pitch)
    k K Q   a contact PAIR, spaced by the cut rule
    r       a metal resistor, never merged with its neighbour
    B A P N D S G   also publish a port of that name
    -       nothing
    0-9     nothing (a digit is a label, not a shape)

A character naming an entry in the file's `patterns` map subdivides its
own cell instead, on the exact fraction so the parts stay on grid.

This is the port of cic-core/src/core/patterntile.{h,cpp}.
"""
import logging

from ...core.cell import Cell
from ...core.port import Port
from ...core.rect import Rect
from ..registry import cicclass

log = logging.getLogger("cicpy.compiler")

#- characters that publish a port as well as painting metal
PORT_CHARS = "BAPNDSG"
#- characters that paint the plain cell-sized rectangle
BOX_CHARS = "xXKkCQrc"


def setBox(rect, x, y, width, height):
    """setRect(x,y,w,h) -- cicpy's Rect.setRect copies another Rect."""
    rect.x1, rect.x2 = (x + width, x) if width < 0 else (x, x + width)
    rect.y1, rect.y2 = (y + height, y) if height < 0 else (y, y + height)


def snap(v, grid):
    """Round to the manufacturing grid, halfway away from zero.

    A sub pattern divides one column into xcount parts and the pitch is
    not generally divisible by that. Truncating each step puts every
    boundary off grid and piles the remainder at the right edge, so
    compute each boundary from the exact fraction and snap it.
    """
    if grid <= 0:
        return int(v)
    q = (v + grid // 2) // grid if v >= 0 else (v - grid // 2) // grid
    return int(q * grid)


class PatternData():
    """One entry of the file's `patterns` map."""

    def __init__(self, name, pattern):
        self.name = name
        self.pattern = list(pattern)
        self.ycount = len(self.pattern)
        self.xcount = max((len(s) for s in self.pattern), default=0)

    def getRectangles(self, r, grid=0):
        """Subdivide `r` into this pattern's marked cells."""
        rects = []
        if r is None or not self.xcount or not self.ycount:
            return rects
        x1, y1, x2, y2 = r.x1, r.y1, r.x2, r.y2
        xat = [snap(x1 + (x2 - x1) * i // self.xcount, grid)
               for i in range(self.xcount + 1)]
        yat = [snap(y1 + (y2 - y1) * i // self.ycount, grid)
               for i in range(self.ycount + 1)]

        prev = None
        for y in range(self.ycount):
            s = self.pattern[y]
            for x in range(self.xcount):
                if x >= len(s) or s[x] != "x":
                    continue
                #- a run of marked cells is ONE rectangle, not several
                if prev is not None and prev.x2 == xat[x]:
                    prev.setRight(xat[x + 1])
                else:
                    ra = Rect(r.layer, xat[x], yat[y],
                              xat[x + 1] - xat[x], yat[y + 1] - yat[y])
                    rects.append(ra)
                    prev = ra
        return rects


@cicclass("cIcCore::PatternTile")
class PatternTile(Cell):

    def __init__(self, name=""):
        super().__init__(name)
        self.xspace_ = 0
        self.yspace_ = 0
        self.xmax_ = 0
        self.ymax_ = 0
        self.arraylength = 0
        self.minPolyLength = 0
        self.horizontalGrid = 0
        self.verticalGrid = 0
        self.horizontalGridMultiplier = 1.0
        self.verticalGridMultiplier = 1.0
        self.mirrorPatternString = 0
        self.polyWidthAdjust = 1
        self.metalUnderMetalRes = False
        self.xoffset = 0
        self.yoffset = 0
        self.widthoffset = 0
        self.heightoffset = 0
        self.verticalMultiplyVector_ = []
        #- rectangle_strings[layer][x][y] = char
        self.rectangle_strings = {}
        self.rectangles = {}
        self.layers = {}
        self.layerNames = []
        self.copyRow_ = []
        self.copyColumn_ = []
        self.copyLayer_ = []
        self.enclosures_ = []
        self.enclosureRectangles_ = []
        #- the file's `patterns`, set by the compiler before the hooks run
        self.patterns = {}
        self.Pattern = {}
        self.prev_rect_ = None
        self.currentHeight_ = 0
        self.currentHeightDelta_ = 0

    #- -----------------------------------------------------------------
    #- Rules
    #- -----------------------------------------------------------------

    def rules(self):
        from ...core.rules import Rules
        return Rules.getInstance()

    def rule(self, layer, key, default=0):
        """Rules.get RAISES on a missing rule, so ask forgivingly."""
        try:
            v = self.rules().get(layer, key)
        except Exception:
            return default
        return default if v is None else v

    def grid(self):
        return getattr(self.rules(), "grid", 0) * 10

    def getRuleForHorizontalGrid(self, ar):
        if not isinstance(ar, list) or len(ar) < 2:
            log.error("getRuleForHorizontalGrid needs at least two elements")
            return
        self.horizontalGrid = self.rule(ar[0], ar[1])

    def getRuleForVerticalGrid(self, ar):
        if not isinstance(ar, list) or len(ar) < 2:
            log.error("getRuleForVerticalGrid needs at least two elements")
            return
        self.verticalGrid = self.rule(ar[0], ar[1])

    #- -----------------------------------------------------------------
    #- The vertical multiply vector: rows that are not all one pitch
    #- -----------------------------------------------------------------

    def verticalMultiplyVector(self, ar):
        for v in ar or []:
            self.verticalMultiplyVector_.append(float(v))

    def verticalMultiplyVectorSum(self, y):
        vmv = self.verticalMultiplyVector_
        if y >= 0 and len(vmv) >= y:
            return sum(vmv[:y])
        return y

    def translateX(self, x):
        return int((x + self.xoffset) * self.xspace_)

    def translateY(self, y):
        yt = self.yoffset * self.yspace_
        yt += self.verticalMultiplyVectorSum(y) * self.yspace_
        return int(yt)

    #- -----------------------------------------------------------------
    #- Grid construction
    #- -----------------------------------------------------------------

    def copyRow(self, obj):
        self.copyRow_.append(self._copySpec(obj))

    def copyColumn(self, obj):
        self.copyColumn_.append(self._copySpec(obj))

    def _copySpec(self, obj):
        obj = dict(obj or {})
        return {"count": int(obj.get("count", 0)),
                "length": int(obj.get("length", 0)),
                "offset": int(obj.get("offset", 0)),
                #- position defaults to offset: copy in place
                "position": int(obj.get("position", obj.get("offset", 0)))}

    def copyLayer(self, ar):
        if isinstance(ar, list) and len(ar) >= 2:
            self.copyLayer_.append({"from": ar[0], "to": ar[1]})

    def fillCoordinatesFromString(self, ar):
        """Read one layer's picture into the coordinate grid."""
        if not isinstance(ar, list) or not ar:
            return

        self.xspace_ = self.rule("ROUTE", "horizontalgrid") * self.horizontalGridMultiplier
        self.yspace_ = self.rule("ROUTE", "verticalgrid") * self.verticalGridMultiplier
        if self.horizontalGrid:
            self.xspace_ = self.horizontalGrid
        if self.verticalGrid:
            self.yspace_ = self.verticalGrid
        if self.minPolyLength == 0:
            self.minPolyLength = self.rule("PO", "mingatelength")

        layer = ar[0]
        rows = list(ar[1:])

        if self.arraylength == 0:
            self.arraylength = len(rows)
        if self.arraylength != len(rows):
            log.error("%s: layer %s does not have %d lines",
                      self.name, layer, self.arraylength)

        for cl in self.copyLayer_:
            if layer == cl["from"]:
                self.fillCoordinatesFromString([cl["to"]] + rows)

        rows = self.applyCopyRows(rows)

        strs = []
        for i, row in enumerate(rows):
            row = self.applyCopyColumns(row)
            if self.mirrorPatternString:
                row = row[::-1]

            #- the FIRST string is the top row, so y counts down from the
            #- last: the picture reads the way the layout looks
            y = len(rows) - i - 1
            for x, c in enumerate(row):
                if y > self.ymax_:
                    self.ymax_ = y
                if x > self.xmax_:
                    self.xmax_ = x
                if c.isdigit():
                    continue
                if c != "-":
                    self.rectangle_strings.setdefault(layer, {}).setdefault(x, {})[y] = c
            strs.append(row)

        self.layers[layer] = strs
        if layer not in self.layerNames:
            self.layerNames.append(layer)

    def applyCopyRows(self, rows):
        for c in self.copyRow_:
            if len(rows) < c["offset"]:
                log.warning("%s: copyRow offset too large for %d rows", self.name, len(rows))
                continue
            if len(rows) < c["offset"] + c["length"]:
                log.warning("%s: copyRow offset+length too large for %d rows",
                            self.name, len(rows))
                continue
            block = rows[c["offset"]:c["offset"] + c["length"]]
            for _ in range(c["count"]):
                for s in block:
                    rows.insert(c["position"], s)
        return rows

    def applyCopyColumns(self, row):
        for c in self.copyColumn_:
            if len(row) < c["offset"]:
                log.warning("%s: copyColumn offset too large", self.name)
                continue
            block = row[c["offset"]:c["offset"] + c["length"]]
            for _ in range(c["count"]):
                row = row[:c["position"]] + block + row[c["position"]:]
        return row

    #- -----------------------------------------------------------------
    #- Enclosures
    #- -----------------------------------------------------------------

    def addEnclosure(self, ar):
        if isinstance(ar, list) and len(ar) >= 2:
            self.enclosures_.append({"layer": ar[0], "startx": 0,
                                     "encloseWithLayers": list(ar[1:])})

    def addEnclosuresByRectangle(self, ar):
        self.addEnclosureByRectangle(ar)

    def addEnclosureByRectangle(self, ar):
        if not isinstance(ar, list) or len(ar) < 5:
            return
        self.enclosureRectangles_.append({
            "layer": ar[0], "x1": float(ar[1]), "y1": float(ar[2]),
            "width": float(ar[3]), "height": float(ar[4]),
            "encloseWithLayers": [str(v) for v in ar[5:]]})

    def paintEnclosures(self):
        """Draw a layer over the extent of the layers it must enclose."""
        for e in self.enclosureRectangles_:
            r = Rect(e["layer"], self.translateX(int(e["x1"])),
                     self.translateY(int(e["y1"])),
                     int(e["width"] * self.xspace_), int(e["height"] * self.yspace_))
            self.add(r)
            self.onPaintEnclosure(r)

        for e in self.enclosures_:
            rects = []
            for lay in e["encloseWithLayers"]:
                rects += self.findPatternRects(lay)
            if not rects:
                continue
            x1 = min(r.x1 for r in rects)
            y1 = min(r.y1 for r in rects)
            x2 = max(r.x2 for r in rects)
            y2 = max(r.y2 for r in rects)
            r = Rect(e["layer"], x1, y1, x2 - x1, y2 - y1)
            self.add(r)
            self.onPaintEnclosure(r)

    def findPatternRects(self, layer):
        out = []
        for _y, row in self.rectangles.get(layer, {}).items():
            for _x, r in row.items():
                if r is not None:
                    out.append(r)
        return out

    #- -----------------------------------------------------------------
    #- Subclass hooks -- no-ops on a plain tile
    #- -----------------------------------------------------------------

    def onFillCoordinate(self, c, layer, x, y, data):
        pass

    def endFillCoordinate(self, data):
        pass

    def paintRect(self, rect, c, x, y):
        pass

    def onPaintEnclosure(self, rect):
        pass

    def onPaintEnd(self):
        pass

    #- -----------------------------------------------------------------
    #- Geometry
    #- -----------------------------------------------------------------

    def readPatterns(self):
        for key, pattern in (self.patterns or {}).items():
            if key:
                self.Pattern[key[0]] = PatternData(key[0], pattern)

    def calcBoundingRect(self):
        x2 = int((self.xmax_ + self.widthoffset) * self.xspace_)
        y2 = self.heightoffset * self.yspace_
        y2 += self.verticalMultiplyVectorSum(self.ymax_) * self.yspace_
        #- one row of pattern has ymax_ == 0 and would come out zero high
        if self.ymax_ == 0:
            y2 = self.yspace_
        r = Rect()
        r.setPoint1(0, 0)
        r.setPoint2(int(x2), int(y2))
        return r

    def place(self):
        pass

    def paint(self):
        if self.horizontalGrid:
            self.xspace_ = self.horizontalGrid
        if self.verticalGrid:
            self.yspace_ = self.verticalGrid
        if self.minPolyLength == 0:
            self.minPolyLength = self.rule("PO", "mingatelength")

        self.readPatterns()

        for layer in self.layerNames:
            strs = self.layers[layer]
            for y in range(self.ymax_ + 1):
                vmv = 1.0
                if len(self.verticalMultiplyVector_) > y:
                    vmv = self.verticalMultiplyVector_[y]
                elif self.verticalMultiplyVector_:
                    log.error("verticalMultiplyVector has no index %d", y)

                self.currentHeight_ = self.yspace_ * vmv
                self.currentHeightDelta_ = self.currentHeight_ - self.yspace_
                ys = self.translateY(y)

                for x in range(self.xmax_ + 1):
                    s = strs[len(strs) - y - 1]
                    if len(s) - 1 < x:
                        log.error("%s: too few columns in '%s'", self.name, s)
                        continue
                    c = s[x]
                    if c == "-":
                        continue
                    self.paintCoordinate(layer, c, x, y, ys, vmv)

        self.updateBoundingRect()
        self.paintEnclosures()
        self.onPaintEnd()

    def paintCoordinate(self, layer, c, x, y, ys, vmv):
        rect = Rect()
        rect.layer = layer
        port = None
        xs = self.translateX(x)

        #- poly is sized by its own rule, never by the row pitch
        if layer == "PO":
            self.currentHeight_ = self.rule(layer, "width") + self.currentHeightDelta_
            if self.currentHeight_ < self.minPolyLength:
                self.currentHeight_ = self.minPolyLength + self.currentHeightDelta_
        elif c == "x":
            self.currentHeight_ = self.yspace_ * vmv
        if c == "X" or self.polyWidthAdjust == 0:
            self.currentHeight_ = self.yspace_ * vmv

        lyspace = self.yspace_ * vmv

        if c in PORT_CHARS:
            port = self.getPort(c)
            if port is None:
                port = Port(c)
                self.add(port)
            #- and fall through: a port cell paints its metal too, and
            #- that rectangle is what port.set() picks up below

        if c in PORT_CHARS or c in BOX_CHARS:
            setBox(rect, xs, ys, self.xspace_, self.currentHeight_)
            rect.moveCenter(xs + self.xspace_ / 2.0, ys + lyspace / 2.0)
        elif c == "3":
            setBox(rect, xs, ys, self.xspace_ * 3, self.rule(layer, "height"))
            rect.moveCenter(xs + self.xspace_ / 2.0, ys + lyspace / 2.0)
        elif c == "V":
            setBox(rect, xs, ys - lyspace / 2.0, self.xspace_, lyspace * 2.0)
        elif c == "m":
            setBox(rect, xs, ys, self.xspace_, self.minPolyLength + self.currentHeightDelta_)
            rect.moveCenter(xs + self.xspace_ / 2.0, ys + lyspace / 2.0)
        elif c == "w":
            minw = self.rule(layer, "width") + self.currentHeightDelta_
            setBox(rect, xs, ys, self.xspace_, minw)
            rect.moveCenter(xs + self.xspace_ / 2.0, ys + lyspace / 2.0)
            self.currentHeight_ = minw

        #- a character naming a sub pattern subdivides its own cell, and
        #- the cell rectangle itself is then not drawn
        if c in self.Pattern:
            setBox(rect, xs, ys, self.xspace_, lyspace)
            for r in self.Pattern[c].getRectangles(rect, self.grid()):
                self.add(r)
            setBox(rect, xs, ys, 0, 0)

        #- a gate is the minimum gate length, whatever the row pitch says
        if c == "G" and layer == "PO":
            setBox(rect, xs, ys, self.xspace_, self.minPolyLength + self.currentHeightDelta_)
            rect.moveCenter(xs + self.xspace_ / 2.0, ys + lyspace / 2.0)

        #- merge with the neighbour to the left, EXCEPT a metal resistor:
        #- merging one would change the resistance it exists to define
        if c != "r" and self.prev_rect_ is not None and self.prev_rect_.abutsLeft(rect):
            self.prev_rect_.setRight(rect.x2)
            rect = self.prev_rect_
        elif not rect.empty() and rect not in self.children:
            if c == "r" and not self.metalUnderMetalRes:
                #- some technologies refuse metal under a metal resistor
                pass
            else:
                self.add(rect)
                self.rectangles.setdefault(layer, {}).setdefault(y, {})[x] = rect
                self.prev_rect_ = rect

        if port is not None:
            port.set(rect)

        self.paintCuts(layer, c, xs, ys, lyspace)
        self.paintRect(rect, c, x, y)

    def paintCuts(self, layer, c, xs, ys, lyspace):
        """A contact character also drops a cut on the next layer up."""
        if c not in "cCkKQ":
            return
        lay = self.rules().getNextLayer(layer)
        if not lay:
            return
        cw = self.rule(lay, "width")
        ch = self.rule(lay, "height")
        cs = self.rule(lay, "space")

        if c in "cC":
            #- C sits half a pitch over, mirrored with the string
            cxoffset = 0
            if c == "C":
                cxoffset = -self.xspace_ / 2.0 if self.mirrorPatternString \
                    else self.xspace_ / 2.0
            cr = Rect()
            cr.layer = lay
            setBox(cr, xs, ys, cw, ch)
            cr.moveCenter(xs - cxoffset + self.xspace_ / 2.0, ys + lyspace / 2.0)
            self.add(cr)
            return

        #- k K Q are a PAIR of cuts, spaced by the cut rule
        cr = Rect()
        cr.layer = lay
        setBox(cr, xs, ys, cw, ch)
        cxoffset = self.xspace_ / 2.0
        if c == "K":
            cxoffset = self.xspace_ if self.mirrorPatternString else 0
        elif c == "Q":
            cxoffset = -self.xspace_ / 2.0 if self.mirrorPatternString \
                else self.xspace_ / 2 + cs / 2 + cr.width() / 2

        cr1 = cr.getCopy()
        cr.moveCenter(xs + cxoffset, ys + lyspace / 2.0)
        if self.mirrorPatternString:
            cr1.moveCenter(cr.centerX() + cs + cw, cr.centerY())
        else:
            cr1.moveCenter(cr.centerX() - cs - cw, cr.centerY())
        self.add(cr)
        self.add(cr1)
