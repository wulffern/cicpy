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
        print(self,excludeInstances,includeInstances,layer)  
        rects = list()
        for p in self.ports:
            i = p.parent
            if(i is None):
                continue
            if(not i.isInstance()):
                continue

            instanceName = getattr(i, 'instanceName', '')
            # Exclude instances that match the exclude pattern
            if(excludeInstances != "" and (re.search(excludeInstances, instanceName) \
                or re.search(excludeInstances, getattr(i,'name','')))):
                continue
            # Include only instances that match the include pattern
            if(includeInstances != "" and not (re.search(includeInstances, getattr(i,'name','')) \
                or re.search(includeInstances, instanceName))):
                continue
            #print(includeInstances,instanceName)
            rp = p.get(layer)
            if(rp is None): rp = p.get()
            if(rp is not None):
                rects.append(rp)
        return rects
