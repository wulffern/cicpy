#!/usr/bin/env python3
"""Layout cell decorators.

An object file's "decorator" key names classes that hook into the cell
lifecycle alongside the cell's own methods (C++ LayoutCellDecorator):

    "decorator" : [ {"ConnectSourceDrain": ["M1", "||", ""]} ]

Each entry instantiates the named class, hands it the JSON value, and
the compiler calls its stage hooks around place/route/paint in the
reference's exact order.
"""

import logging

log = logging.getLogger(__name__)

DECORATORS = {}


def decorator(name):
    def wrap(cls):
        DECORATORS[name] = cls
        return cls
    return wrap


class LayoutCellDecorator:

    def __init__(self):
        self.layoutcell = None
        self.jsonval = None

    def setOptions(self, jv):
        self.jsonval = jv
        self.parseOptions()

    def setCell(self, lc):
        self.layoutcell = lc

    def parseOptions(self):
        pass

    def afterNew(self):
        pass

    def beforePlace(self):
        pass

    def place(self):
        pass

    def afterPlace(self):
        pass

    def beforeRoute(self):
        pass

    def afterRoute(self):
        pass

    def beforePaint(self):
        pass

    def paint(self):
        pass

    def afterPaint(self):
        pass


@decorator("ConnectSourceDrain")
class ConnectSourceDrain(LayoutCellDecorator):
    """Wire each transistor's drain to the next one's source.

    Walks the cell's PatternTransistor instances in placement order;
    within a group, SD<i> routes prev:D to this:S on the given layer
    (cIcCore::ConnectSourceDrain, "have to assume drain is on top").
    """

    def parseOptions(self):
        jobj = self.jsonval if isinstance(self.jsonval, list) else []
        if len(jobj) < 3:
            log.error("ConnectSourceDrain needs [layer, routeType, options]")
            self.layer = self.routeType = self.options = ""
            return
        self.layer = str(jobj[0])
        self.routeType = str(jobj[1])
        self.options = str(jobj[2])

    def beforeRoute(self):
        lc = self.layoutcell
        if lc is None:
            return
        from ..core.route import Route

        transistors = []
        for ch in lc.children:
            if ch is None or not ch.isInstance():
                continue
            cell = getattr(ch, "layoutcell", None)
            #- the exact class, as the C++ strcmp: a high resistor is
            #- a PatternTile too and must not be chained
            if cell is not None and type(cell).__name__ == "PatternTransistor":
                transistors.append(ch)

        if not transistors:
            return

        prev = transistors[0]
        prev_group = getattr(getattr(prev, "subcktInstance", None), "groupName", "")
        prev_name = prev.instanceName
        for i in range(1, len(transistors)):
            inst = transistors[i]
            group = getattr(getattr(inst, "subcktInstance", None), "groupName", "")
            name = inst.instanceName
            if prev_group == group:
                start = lc.findAllRectangles(prev_name + ":D", self.layer)
                stop = lc.findAllRectangles(name + ":S", self.layer)
                if start and stop:
                    r = Route("SD%d" % i, self.layer, start, stop,
                              self.options, self.routeType)
                    lc.add(r)
            prev_group = group
            prev_name = name
