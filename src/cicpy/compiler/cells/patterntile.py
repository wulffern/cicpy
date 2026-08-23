#!/usr/bin/env python3
"""PatternTile -- a cell drawn from a character grid.

An object file gives PatternTile a picture of the cell, one string per
row, one character per column:

    ["PO", "XXXXXXX",
           "X-----X",
           "XXXXXXX"]

Each character that is not `-` and not a digit marks a coordinate on
that layer; `paint()` turns the marked coordinates into rectangles on
a grid taken from the technology rules. A character may also name an
entry in the file's `patterns` map, which subdivides its column.

This is the port of cic-core/src/core/patterntile.{h,cpp}. The grid
build is complete; paint() is not yet, and says so rather than
quietly emitting a cell with no geometry.
"""
import logging

from ...core.cell import Cell
from ..registry import cicclass

log = logging.getLogger("cicpy.compiler")


class NotPortedYet(NotImplementedError):
    """Raised where the C++ still has behaviour this port does not."""


@cicclass("cIcCore::PatternTile")
class PatternTile(Cell):

    #- file-level `patterns`, shared by every tile in a compile
    Patterns = {}

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
        self.xoffset = 0
        self.yoffset = 0
        self.widthoffset = 0
        self.heightoffset = 0
        #- rectangle_strings_[layer][x][y] = char
        self.rectangle_strings = {}
        self.layers = {}
        self.layerNames = []
        self.copyRow_ = []
        self.copyColumn_ = []
        self.copyLayer_ = []
        self.enclosures_ = []
        self.patterns = {}

    #- -----------------------------------------------------------------
    #- Grid construction
    #- -----------------------------------------------------------------

    def copyRow(self, obj):
        self.copyRow_.append(dict(obj))

    def copyColumn(self, obj):
        self.copyColumn_.append(dict(obj))

    def copyLayer(self, ar):
        if isinstance(ar, list) and len(ar) >= 2:
            self.copyLayer_.append({"from": ar[0], "to": ar[1]})

    def getRuleForHorizontalGrid(self, ar):
        """Take the horizontal grid from a technology rule, not a number."""
        rules = self.rules()
        if rules is None or not isinstance(ar, list) or len(ar) < 2:
            return
        self.horizontalGrid = rules.get(ar[0], ar[1])

    def getRuleForVerticalGrid(self, ar):
        rules = self.rules()
        if rules is None or not isinstance(ar, list) or len(ar) < 2:
            return
        self.verticalGrid = rules.get(ar[0], ar[1])

    def rules(self):
        try:
            from ...core.rules import Rules
            return Rules.getInstance()
        except Exception:
            return None

    def fillCoordinatesFromString(self, ar):
        """Read one layer's picture into the coordinate grid."""
        if not isinstance(ar, list) or not ar:
            return

        rules = self.rules()
        if rules is not None:
            self.xspace_ = rules.get("ROUTE", "horizontalgrid") * self.horizontalGridMultiplier
            self.yspace_ = rules.get("ROUTE", "verticalgrid") * self.verticalGridMultiplier
            if self.minPolyLength == 0:
                self.minPolyLength = rules.get("PO", "mingatelength")
        if self.horizontalGrid:
            self.xspace_ = self.horizontalGrid
        if self.verticalGrid:
            self.yspace_ = self.verticalGrid

        layer = ar[0]
        rows = list(ar[1:])

        if self.arraylength == 0:
            self.arraylength = len(rows)
        if self.arraylength != len(rows):
            log.error("%s: layer %s does not have %d lines",
                      self.name, layer, self.arraylength)

        #- a layer marked for copying is filled again under the new name
        for cl in self.copyLayer_:
            if layer == cl["from"]:
                self.fillCoordinatesFromString([cl["to"]] + rows)

        rows = self.applyCopyRows(rows)

        strs = []
        for i, row in enumerate(rows):
            row = self.applyCopyColumns(row)
            if self.mirrorPatternString:
                row = row[::-1]

            #- row 0 is the TOP of the picture, so y counts down from the
            #- last row: the string reads the way the layout looks
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
            offset, length = int(c.get("offset", 0)), int(c.get("length", 0))
            count, position = int(c.get("count", 0)), int(c.get("position", 0))
            if len(rows) < offset:
                log.warning("%s: copyRow offset too large for %d rows", self.name, len(rows))
                continue
            if len(rows) < offset + length:
                log.warning("%s: copyRow offset+length too large for %d rows", self.name, len(rows))
                continue
            block = rows[offset:offset + length]
            for _ in range(count):
                for s in block:
                    rows.insert(position, s)
        return rows

    def applyCopyColumns(self, row):
        for c in self.copyColumn_:
            offset, length = int(c.get("offset", 0)), int(c.get("length", 0))
            count, position = int(c.get("count", 0)), int(c.get("position", 0))
            if len(row) < offset:
                log.warning("%s: copyColumn offset too large", self.name)
                continue
            block = row[offset:offset + length]
            for _ in range(count):
                row = row[:position] + block + row[position:]
        return row

    #- -----------------------------------------------------------------
    #- Geometry
    #- -----------------------------------------------------------------

    def addEnclosure(self, ar):
        if isinstance(ar, list) and len(ar) >= 2:
            self.enclosures_.append({"layer": ar[0], "startx": 0,
                                     "encloseWithLayers": list(ar[1:])})

    def addEnclosureByRectangle(self, ar):
        self.addEnclosure(ar)

    def place(self):
        pass

    def paint(self):
        """Turn the coordinate grid into rectangles.

        PatternTile::paint() in the C++ is ~280 lines: it walks each
        layer's coordinates, groups runs into rectangles, applies the
        per-character sub-patterns from `patterns`, snaps to the
        manufacturing grid, and then paints enclosures over the result.
        None of that is ported yet.

        Failing loudly is the point. A PatternTile that silently
        painted nothing would come out of the compiler as a valid,
        empty cell and the parity harness would score it as a shape
        count of zero rather than as work still to do.
        """
        if not self.rectangle_strings:
            return
        raise NotPortedYet(
            "PatternTile.paint() is not ported: cell '%s' has %d layer(s) of "
            "coordinates (%s) that would become geometry. See "
            "cic-core/src/core/patterntile.cpp:348" % (
                self.name, len(self.rectangle_strings),
                ",".join(sorted(self.rectangle_strings))))
