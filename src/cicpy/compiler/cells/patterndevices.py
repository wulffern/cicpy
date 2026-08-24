#!/usr/bin/env python3
"""The pattern DEVICES: a tile that also knows what it is electrically.

PatternTransistor, PatternResistor and PatternCapacitor draw exactly
what PatternTile draws -- the picture is the layout -- and use the
fill/paint hooks to keep a SPICE view in step with it: the transistor
measures its own width, length and finger count off the grid, the
resistor and capacitor drop resistor-layer paint under every `r`.

Ports of cic-core/src/core/pattern{transistor,resistor,capacitor}.cpp.
"""
import logging

import cicspi

from ..registry import cicclass
from .patterntile import PatternTile

log = logging.getLogger("cicpy.compiler")

INT_MIN = -2**31


def _device(name, nodes):
    d = cicspi.Device()
    d.name = name
    d.nodes = list(nodes)
    return d


def _subcktWith(name, dev):
    ckt = cicspi.Subckt()
    ckt.name = name
    ckt.nodes = list(dev.nodes)
    ckt.addInstance(dev)
    return ckt


@cicclass("cIcCore::PatternTransistor")
class PatternTransistor(PatternTile):
    """A tile whose picture is a MOS device.

    The geometry hooks measure the device: each PO gate row over OD
    bumps the finger count, the OD extent sets the width, and `m`
    marks a minimum-length gate.
    """

    def __init__(self, name=""):
        super().__init__(name)
        self.mos = _device("M1", ["D", "G", "S", "B"])
        self.subckt = _subcktWith(self.name or "MOS", self.mos)
        self.ckt = self.subckt

    #- `type` in an object file, through the name translator
    def mosType(self, value):
        self.mos.deviceName = str(value)

    def initFillCoordinates(self):
        return {"isTransistor": False, "wmin": 2**31, "wmax": INT_MIN,
                "pofinger": 0, "nf": 0, "useMinLength": False}

    def onFillCoordinate(self, c, layer, x, y, data):
        if layer == "PO" and c == "G":
            if data["pofinger"] != y:
                data["nf"] += 1
            data["pofinger"] = y
        od = self.rectangle_strings.get("OD", {})
        if layer == "PO" and x in od and y in od[x]:
            data["isTransistor"] = True
            data["wmin"] = min(data["wmin"], x)
            data["wmax"] = max(data["wmax"], x)
            if c == "m":
                data["useMinLength"] = True

    def endFillCoordinate(self, data):
        if not data["isTransistor"]:
            return
        width = (data["wmax"] - data["wmin"] + 1) * self.xspace_
        minlength = self.minPolyLength or self.rule("PO", "mingatelength")
        self.mos.properties["width"] = self.toMicron(width)
        self.mos.properties["length"] = self.toMicron(minlength)
        self.mos.properties["nf"] = data["nf"]
        self.mos.properties["drainWidth"] = self.toMicron(self.yspace_)
        self.mos.properties["sourceWidth"] = self.toMicron(self.yspace_)

    def paintRect(self, rect, c, x, y):
        od = self.rectangle_strings.get("OD", {})
        if rect.layer == "PO" and x in od and y in od[x]:
            self.mos.properties["length"] = self.toMicron(rect.height())


class _ResLayerMixin:
    """Shared `r` handling: paint the layer's resistor marker."""

    def paintResRect(self, r, c, x, y):
        if c != "r" or r is None:
            return None
        layer = self.rules().getLayer(r.layer)
        res = getattr(layer, "res", "") if layer else ""
        if not res:
            return None
        from ...core.rect import Rect
        rc = Rect(res, self.translateX(x), self.translateY(y),
                  self.xspace_, self.currentHeight_)
        return rc


@cicclass("cIcCore::PatternResistor")
class PatternResistor(_ResLayerMixin, PatternTile):
    """A tile whose picture is a resistor: `r` paints the res marker."""

    def __init__(self, name=""):
        super().__init__(name)
        self.res = _device("R1", ["A", "B"])
        self.subckt = _subcktWith(self.name or "RES", self.res)
        self.ckt = self.subckt

    def initFillCoordinates(self):
        return {"pofinger": 0, "nf": 0}

    def onFillCoordinate(self, c, layer, x, y, data):
        if data["pofinger"] < x:
            data["nf"] += 1
            data["pofinger"] = x
        if layer == "PO":
            self.res.properties["width"] = self.toMicron(self.xspace_)

    def paintRect(self, rect, c, x, y):
        rc = self.paintResRect(rect, c, x, y)
        if rc is not None:
            self.add(rc)
            self.res.properties["width"] = self.toMicron(self.currentHeight_)
            self.res.properties["length"] = self.toMicron(self.xspace_)
            self.res.properties["layer"] = rect.layer


@cicclass("cIcCore::PatternHighResistor")
class PatternHighResistor(PatternResistor):
    """A poly resistor with a bulk tie: its device is an `rppo` on
    N/P/B, its length is measured off the OP enclosure, and
    `transposed` runs the stripes across the cell instead of up it.
    """

    def __init__(self, name=""):
        super().__init__(name)
        self.transposed = False
        self.res = _device("R1", ["N", "P", "B"])
        self.res.deviceName = "rppo"
        self.subckt = _subcktWith(self.name or "RES", self.res)
        self.ckt = self.subckt

    def onFillCoordinate(self, c, layer, x, y, data):
        if not str(layer).startswith("PO"):
            return
        if self.transposed:
            #- stripes run ACROSS, so a finger is a row; the fill loop
            #- walks y downward, so count row CHANGES, not maxima
            if data.get("porow") != y:
                data["nf"] = data.get("nf", 0) + 1
                data["porow"] = y
            self.res.properties["width"] = self.toMicron(self.yspace_)
        else:
            if data["pofinger"] < x:
                data["nf"] += 1
                data["pofinger"] = x
            self.res.properties["width"] = self.toMicron(self.xspace_)

    def onPaintEnclosure(self, r):
        if r is not None and r.layer == "OP":
            #- the OP rectangle spans the resistor; its LONG side is
            #- the length, and which side that is follows orientation
            self.res.properties["length"] = self.toMicron(
                r.width() if self.transposed else r.height())

    def endFillCoordinate(self, data):
        if "nf" in data:
            self.res.properties["nf"] = data["nf"]


@cicclass("cIcCore::PatternHighResistorNoBulk",
          "cIcCore::PatternHighResistorNobulk")
class PatternHighResistorNoBulk(PatternHighResistor):
    """The bulk-less variant: same rppo device on N/P only."""

    def __init__(self, name=""):
        super().__init__(name)
        self.res = _device("R1", ["N", "P"])
        self.res.deviceName = "rppo"
        self.subckt = _subcktWith(self.name or "RES", self.res)
        self.ckt = self.subckt


@cicclass("cIcCore::PatternCapacitor")
class PatternCapacitor(_ResLayerMixin, PatternTile):
    """A tile whose picture is a capacitor.

    Each port character becomes a node reached through a small series
    resistor -- the electrical model of the plate it lands on -- and
    `r` paints the resistor marker exactly as PatternResistor does.
    """

    def __init__(self, name=""):
        super().__init__(name)
        self.subckt = cicspi.Subckt()
        self.subckt.name = self.name or "CAP"
        self.subckt.nodes = []
        self.ckt = self.subckt
        self.resistors = []
        self._rindex = 0
        self._rcounter = 0
        self._nodes = []

    def onFillCoordinate(self, c, layer, x, y, data):
        if c in "BAPNDSG":
            res = _device("R%d" % (self._rindex + 1),
                          [str(c), "NC%d" % self._rindex])
            self._rindex += 1
            self._nodes.append(str(c))
            self.subckt.nodes = list(self._nodes)
            self.subckt.addInstance(res)
            self.resistors.append(res)
            res.properties["layer"] = layer

    def onPaintEnd(self):
        self.subckt.setProperty("width", self.toMicron(self.width()))
        self.subckt.setProperty("height", self.toMicron(self.height()))

    def paintRect(self, rect, c, x, y):
        rc = self.paintResRect(rect, c, x, y)
        if rc is None:
            return
        if len(self.resistors) > self._rcounter:
            r = self.resistors[self._rcounter]
            r.properties["width"] = self.toMicron(self.currentHeight_)
            r.properties["length"] = self.toMicron(self.xspace_)
            r.properties["layer"] = rect.layer
            self._rcounter += 1
        self.add(rc)
