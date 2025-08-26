#!/usr/bin/env python3
import re
class Graph():

    def __init__(self):
        self.ports = list()
        self.name = ""

    def append(p:Port):
        if(not self.ports.contains(p)):
            self.ports.append(p)

    def getRectangles(excludeInstances:str,includeInstances:str,layer:str):
        rects = list()
        for p in self.ports:
            i = p.parent()
            if(i is None):continue
            if(not i.isInstance()): continue

            if(excludeInstances is not None):
                if( re.search(excludeInstances,i.instanceName) \
                    or re.search(excludeInstances,i.name)): continue

            if(includeInstances is not None):
                if(not ( re.search(includeInstances,i.instanceName) \
                    or re.search(includeInstances,i.name))): continue
            rp = p.get(layer)

            if(rp is  None): rp = p.get()
            if(rp is not None):
                rects.append(rp)
