#!/usr/bin/env python3
import re
import os
import cicpy as cic

class Magic(cic.LayoutCell):

    def __init__(self):
        super().__init__()
        self.magscale = 1
        self.techlib = "nmos"
        self.timestamp = 0
        pass

    def toAngstrom(self,val):
        return int(val)/self.magscale*100

    def boxToRect(self,box,layer="PR"):
        r = cic.Rect(layer)
        r.x1 = self.toAngstrom(box[0])
        r.y1 = self.toAngstrom(box[1])
        r.x2 = self.toAngstrom(box[2])
        r.y2 = self.toAngstrom(box[3])
        return r


    
    def parseToken(self,token,category,line):


        if(category== ""):
            if(token == "magscale"):
                ar = line.split(" ")
                self.magscale = int(ar[1])
            #- Beginning of file
            pass
        elif(category == "properties"):
            if(line.startswith("FIXED_BBOX")):
                bbox = re.findall("FIXED_BBOX\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",line)
                r = self.boxToRect(bbox[0])
                self.setRect(r)
        elif(token == "tech"):
            self.techlib = line

        else:
            pass



    def readFromFile(self,fname):
        self.name = os.path.basename(fname).replace(".mag","")
        lib = os.path.basename(os.path.dirname(fname))
        self.libpath = lib


        with open(fname) as fi:
            buff = ""
            pcount = 0
            ind =0
            category = ""
            for line in fi:
                #- Keep track of category
                m = re.search("<<\s+(\S+)\s+>>",line)
                if(m):
                    category = m.groups()[0]
                else:
                    arr = re.split("\s+",line)
                    token = arr[0]
                    rest = " ".join(arr[1:]).strip()
                    self.parseToken(token,category,rest)

class Layout(Magic):
    pass
