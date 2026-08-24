#!/usr/bin/env python3

from .cell import Cell
from .port import Port
from .rect import Rect
from .rules import Rules

class InstancePort(Port):

    #- an instance port is geometry in the PARENT's frame and folds
    #- with the instance; only a cell's own Port follows its rect.
    #- The C++ overrides these straight back to Rect's fold.
    def mirrorY(self, ax):
        Rect.mirrorY(self, ax)

    def mirrorX(self, ay):
        Rect.mirrorX(self, ay)

    def __init__(self,name,port:Port,parent:Cell):
        super().__init__(name)
        self.childport = port
        self.parent = parent
        self.childName = port.name
        r = port.get()
        rules = Rules.getInstance()
        if(r):
            l = rules.getLayer(r.layer)
            self.routeLayer = l.name
            self.setRect(r)

    def toJson(self):
        """...AND the child port's own name.

        An InstancePort is the join between a parent net and the child
        port it is wired to, and `childName` is the only record of that
        pairing -- the geometry cannot recover it, because a wrapper
        republishes its ports at rects of its own choosing (measured:
        LELOTEMP_CMPR's VIP port sits at y 137000 in its own frame and
        the instance port for it resolves to y 77000).

        Without this the pairing survived only in memory, so anything
        reading a .cic saw a plain Port and had to treat the child's
        name and the parent's as two different nets. That is what made
        checkroutes report five shorts on a cell netgen matched
        uniquely.
        """
        o = super().toJson()
        #- "Port", not "InstancePort": that is the class ciccreator
        #- writes and the only one its reader knows, and cicpy's own
        #- readers already treat the two names as the same thing. What
        #- makes it an InstancePort in a file is childName, which stays.
        o["class"] = "Port"
        if self.childName:
            o["childName"] = self.childName
        return o
