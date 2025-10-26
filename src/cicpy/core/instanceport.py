#!/usr/bin/env python3

from .cell import Cell
from .port import Port
from .rules import Rules

class InstancePort(Port):

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
