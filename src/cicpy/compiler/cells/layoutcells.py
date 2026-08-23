#!/usr/bin/env python3
"""Cell classes backed by cicpy's own LayoutCell."""
import logging

from ...core.layoutcell import LayoutCell as _CicpyLayoutCell
from ..registry import cicclass

log = logging.getLogger("cicpy.compiler")


@cicclass("cIcCore::LayoutCell", "Layout::LayoutCell")
class LayoutCell(_CicpyLayoutCell):
    """cicpy's LayoutCell, under the name object files use for it.

    Most object-file calls land straight on cicpy's own methods: the
    dispatcher spreads the JSON array into their positional arguments
    and the orders already agree. Where they DO NOT agree, the method
    is overridden here to unpack the array the way ciccreator's
    QJsonArray overload does -- this class is the calling convention,
    so the adaptation belongs in it and cicpy's core stays untouched.
    """

    def __init__(self, name=""):
        #- cicpy's LayoutCell takes no name; Cell does
        super().__init__()
        if name:
            self.name = name
        #- object files set this by property; the C++ name has no `set`
        self.patterns = {}
        #- ciccreator's place() ABUTS: a group starts at the previous
        #- instance's x2, no gap (place(): `x = next_x`). The spacing
        #- default on cicpy's LayoutCell is the spi2mag flow's, where
        #- magic cells need the technology's CELL space between them.
        #- This class is the ciccreator calling convention, so it takes
        #- ciccreator's packing.
        self.place_xspace = [0]
        self.place_yspace = [0]

    def addConnectivityRoute(self, *args):
        """[layer, regex, routeType, options, cuts, includeInstances]

        NOT a plain spread. ciccreator reads element 5 into
        includeInstances and leaves excludeInstances empty -- there is
        no element for it -- so spreading positionally would put an
        instance filter into the exclude slot and quietly route the
        complement of what the object file asked for.
        """
        if len(args) != 1 or not isinstance(args[0], list):
            return super().addConnectivityRoute(*args)
        obj = args[0]
        if len(obj) < 3:
            log.error("addConnectivityRoute needs at least three elements")
            return None
        def at(i):
            return str(obj[i]) if len(obj) > i else ""
        return super().addConnectivityRoute(
            at(0), at(1), at(2),
            options=at(3), cuts=at(4),
            excludeInstances="", includeInstances=at(5))

    def addRouteConnection(self, *args):
        """[path, includeInstances, location, layer, options, override]

        NOT a spread: the JSON array puts location THIRD and layer
        fourth, while the positional method takes layer before
        location. C++ addRouteConnection(QJsonArray) does this exact
        shuffle.
        """
        if len(args) != 1 or not isinstance(args[0], list):
            return super().addRouteConnection(*args)
        obj = args[0]
        if len(obj) < 3:
            log.error("addRouteConnection needs at least three elements")
            return None
        def at(i):
            return str(obj[i]) if len(obj) > i else ""
        return super().addRouteConnection(
            at(0), at(1), at(3), at(2),
            options=at(4), routeTypeOverride=at(5))

    def addVia(self, *args):
        """[startlayer, stoplayer, path, hcuts, vcuts, offset, name, yoffset]

        Drop a via on each rect the path finds; `offset`/`yoffset` are
        in ROUTE grid pitches. `name` publishes the via's top metal as
        a named rect for later commands to route to.
        """
        obj = args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
        if len(obj) < 4:
            log.error("addVia needs at least four elements")
            return
        from ...core.cut import Cut
        from ...core.rules import Rules
        startlayer, stoplayer, path = (str(v) for v in obj[:3])
        hcuts = int(obj[3])
        vcuts = int(obj[4]) if len(obj) > 4 else 1
        offset = float(obj[5]) if len(obj) > 5 else 0
        name = str(obj[6]) if len(obj) > 6 else ""
        yoffset = float(obj[7]) if len(obj) > 7 else 0
        rules = Rules.getInstance()
        hg = rules.get("ROUTE", "horizontalgrid")
        vg = rules.get("ROUTE", "verticalgrid")
        for r in self.findAllRectangles(path, startlayer):
            if r is None:
                continue
            inst = Cut.getInstance(startlayer, stoplayer, hcuts, vcuts)
            if inst is None:
                continue
            inst.moveTo(int(r.x1 + offset * hg), int(r.y1 + vg * yoffset))
            if name:
                p = inst.getRect(stoplayer)
                if p is not None:
                    self.named_rects[name] = p
                else:
                    log.error("Unknown rect %s", name)
            self.add(inst)

    def addPortOnRect(self, *args):
        """[port, layer, path?] -- publish a port on a found rect."""
        obj = args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
        if len(obj) < 2:
            log.error("addPortOnRect needs (port, layer[, path])")
            return
        port, layer = str(obj[0]), str(obj[1])
        path = str(obj[2]) if len(obj) > 2 else port
        rects = self.findAllRectangles(path, layer)
        if not rects:
            log.error("Could not find port %s on path %s in layer %s", port, path, layer)
            return
        r = rects[0]
        if r.layer != layer:
            log.error("Layer %s differs from %s on rect %s in layer %s",
                      r.layer, port, path, layer)
            return
        self.updatePort(port, r)

    def addPortVia(self, *args):
        """[startlayer, stoplayer, port, path, vcuts, hcuts, xoff, yoff, name?]

        Drop a via beside each found rect and publish the port on the
        via's TOP metal -- how a buried pin is brought up to where a
        router can land on it.
        """
        obj = args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
        if len(obj) < 8:
            log.error("addPortVia needs at least 8 elements")
            return
        from ...core.cut import Cut
        from ...core.port import Port
        startlayer, stoplayer, port, path = (str(v) for v in obj[:4])
        vcuts, hcuts = int(obj[4]), int(obj[5])
        xoffset, yoffset = float(obj[6]), float(obj[7])
        name = str(obj[8]) if len(obj) > 8 else ""
        for r in self.findAllRectangles(path, startlayer):
            if r is None:
                continue
            inst = Cut.getInstance(startlayer, stoplayer, hcuts, vcuts)
            if inst is None:
                continue
            inst.moveTo(int(r.x2 + xoffset * inst.width()),
                        int(r.centerY() + yoffset * inst.height()))
            rstop = inst.getRect(stoplayer)
            if name:
                self.named_rects[name] = rstop
            if port in self.ports:
                self.ports[port].set(rstop)
            else:
                p = Port(port)
                p.set(rstop)
                self.add(p)
            self.add(inst)


@cicclass("Layout::LayoutDigitalCell")
class LayoutDigitalCell(LayoutCell):
    """A standard-cell-shaped LayoutCell.

    In ciccreator this subclass adds the digital row conventions on top
    of LayoutCell. Everything an object file calls on it is inherited,
    so until those conventions are ported it behaves as a LayoutCell --
    which is right for placement and wrong for the implicit rails.
    """


@cicclass("Layout::LayoutRotateCell", "cIcCore::LayoutRotateCell")
class LayoutRotateCell(LayoutCell):
    """A LayoutCell whose contents are rotated by `rotateAngle`.

    The C++ (core/layoutrotatecell.cpp) replaces place() outright:
    every instance of the subckt lands at the ORIGIN with the cell's
    angle -- the class exists to wrap one cell in an orientation, not
    to arrange anything. It adds no name label, and the golden files
    show none.
    """

    def __init__(self, name=""):
        super().__init__(name)
        self.rotateAngle = ""

    def place(self):
        if self.ckt is None:
            return
        for cktInst in self.ckt.instances:
            inst = self.addInstance(cktInst, 0, 0)
            if inst is None:
                continue
            #- addInstance labels the placement; the rotate cell's C++
            #- hand-rolls the same steps without the label
            for ch in list(inst.children):
                if ch.isType("Text"):
                    inst.children.remove(ch)
            inst.setAngle(self.rotateAngle or "")
        self.updateBoundingRect()
