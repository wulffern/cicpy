#!/usr/bin/env python3
import re
import os
import cicpy as cic

class Magic(cic.LayoutCell):

    def __init__(self):
        super().__init__()
        self.magscale = 1
        self.techlib = "sky130A"
        self.timestamp = 0
        self.bb_x1 = cic.INT_MAX
        self.bb_y1 = cic.INT_MAX
        self.bb_x2 = cic.INT_MIN
        self.bb_y2 = cic.INT_MIN
        self.found_bbox = False
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

    def updateXYs(self,rect):
        x1 = self.toAngstrom(rect[0])
        y1 = self.toAngstrom(rect[1])
        x2 = self.toAngstrom(rect[2])
        y2 = self.toAngstrom(rect[3])

        if(x1 < self.bb_x1):
            self.bb_x1 = x1
        if(x2 > self.bb_x2):
            self.bb_x2 = x2
        if(y1 < self.bb_y1):
            self.bb_y1 = y1
        if(y2 > self.bb_y2):
            self.bb_y2 = y2

    
    def parseToken(self,token,category,line):

        #- Need to read all rectangles to get the bounding box
        #- for cells its use + transform + box (box is local, apply transform to move)

        if(category== ""):
            if(token == "magscale"):
                ar = line.split(" ")
                self.magscale = int(ar[1])
            #- Beginning of file
            pass
        elif(category == "properties"):
            if(line.startswith("FIXED_BBOX")):
                #print(line)
                bbox = re.findall(r"FIXED_BBOX\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",line)
                r = self.boxToRect(bbox[0])
                self.found_bbox = True
                self.setRect(r)
        elif(token == "tech"):
            self.techlib = line

        else:
            if(token == "rect"):
                #print(self.name,line)
                rects = re.findall(r"(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",line)
                if(rects):
                    self.updateXYs(rects[0])

            pass


    def readFromFile(self,fname):
        if("border_" in fname):
            return
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
                m = re.search(r"<<\s+(\S+)\s+>>",line)
                if(m):
                    category = m.groups()[0]
                else:
                    arr = re.split(r"\s+",line)
                    token = arr[0]
                    rest = " ".join(arr[1:]).strip()
                    self.parseToken(token,category,rest)

        if(not self.found_bbox):
            self.x1 = self.bb_x1
            self.x2 = self.bb_x2
            self.y1 = self.bb_y1
            self.y2 = self.bb_y2



class Layout(Magic):
    pass
