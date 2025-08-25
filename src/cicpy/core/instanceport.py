#!/usr/bin/env python3

from .cell import Cell
from .port import Port
from .rules import Rules

class InstancePort(Port):

    def __init__(self,name,port:Port,parent:Cell):
        super().__init__(name)
        self.childport = port
        self.parent = parent
        r = p.get()
        rules = Rules()
        if(r):
            l = rules.getLayer(r.layer)
            self.routeLayer = l
            self.setRect(r.layer,r.x1,r.y1,r.width,r.height)
