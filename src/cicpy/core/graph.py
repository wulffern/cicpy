#!/usr/bin/env python3
import re
class Graph():

    def __init__(self):
        self.ports = list()
        self.name = ""

    def append(self,p):
        if p not in self.ports:
            self.ports.append(p)

    def getRectangles(self,excludeInstances:str,includeInstances:str,layer:str):
        rects = list()
        for p in self.ports:
            i = p.parent
            if(i is None):
                continue
            if(not i.isInstance()):
                continue

            if(excludeInstances):
                if( re.search(excludeInstances,getattr(i,'instanceName','')) \
                    or re.search(excludeInstances,getattr(i,'name',''))):
                    continue

            if(includeInstances):
                if(not ( re.search(includeInstances,getattr(i,'instanceName','')) \
                    or re.search(includeInstances,getattr(i,'name','')))):
                    continue
            rp = p.get(layer)

            if(rp is  None): rp = p.get()
            if(rp is not None):
                rects.append(rp)
        return rects
