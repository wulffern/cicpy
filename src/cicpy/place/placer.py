#!/usr/bin/env python3

import pandas as pd
import re
import numpy as np

class Placer():

    def __init__(self,design,layoutfile,pattern):
        self.design = design
        self.layoutfile = layoutfile
        self.pattern = pattern
        self.readFile(self.layoutfile)

    def snap(self,n):
        return np.round(n*1000)/1000

    def getGroup(self,instName):
        group = re.sub("\(\d+\)","",instName)
        return group

    def getIndex(self,instName):
        m = re.search("\((\d+)\)",instName)
        if(m):
            return int(m.group(1))
        else:
            return 0

    def readFile(self,fname):
        df = pd.read_csv(fname,delimiter=";")
        df["group"] = df["instanceName"].apply(self.getGroup)
        df["index"] = df["instanceName"].apply(self.getIndex)
        df["orientn"] = df["orient"]
        df["xd"] = 0.0
        df["yd"] = 0.0
        df["yn"] = 0.0
        df["xn"] = 0.0
        df["row"] = 0
        df["column"] = 0
        self.df = df.sort_values(["group","index","row","column"])

    def place(self):
        self.placeVertical()

    def setPos(self,i,c,x,y,transform_orient):
        self.df.at[i,"yn"] = y
        self.df.at[i,"xn"] = x
        self.df.at[i,"xd"] =  self.df.at[i,"xn"] - self.df.at[i,"x"]
        self.df.at[i,"yd"] =  self.df.at[i,"yn"] -self.df.at[i,"y"]

        if(self.df.at[i,"orient"] == "MY" or transform_orient == "MY"):
                self.df.at[i,"xd"] += c.toMicron(c.width())
        self.df.at[i,"orientn"] = transform_orient


    dPattern = {
        2 : [
                [0,1],
                [1,0]
        ],
        4 :[
                [1,0,0,1],
                [0,1,1,0]
            ],
        6 : [
                [1,0,1,1,0,1],
                [0,1,0,0,1,0]
            ],
        8 : [
                [1,0,0,1],
                [0,1,1,0],
                [1,0,0,1],
                [0,1,1,0],
            ],
        12 : [
            [1,0,1,1,0,1],
            [0,1,0,0,1,0],
            [1,0,1,1,0,1],
            [0,1,0,0,1,0]
        ],
        16 : [
            [1,1,0,0,0,0,1,1],
            [0,0,1,1,1,1,0,0],
            [1,1,0,0,0,0,1,1],
            [0,0,1,1,1,1,0,0]
        ]

    }

    def placeDiffPair(self):


        # How many instances? I only want to support 2
        dfg = self.df.groupby("group")

        if(len(dfg) != 2):
            raise("Error: I don't know how to layout more other number than 2 transistors in a diff pair")

        cc = dfg["row"].count()
        if(cc[0] != cc[1]):
            raise("Error: I don't know how to layout diffpairs with unequal number of transistors")

        isOdd = cc[0] % 2

        if(isOdd):
            raise("Error: I don't know how to layout diffpairs with odd number of transistors")


        num = cc[0]
        if(num not in self.dPattern):
            raise(f"Error: I don't know how to layout diffpairs with {num*2} transistors")

        #- Make lists of the two sets of devices
        devices = list()
        devices.append(list())
        devices.append(list())
        ind = 0
        for i,d in dfg:
            for ix,x in d.iterrows():
                devices[ind].append(ix)
            ind +=1




        #- Set row and colunn
        pattern = self.dPattern[num]
        rows = len(pattern)
        columns = len(pattern[0])
        for row in range(0,rows):
            for col in range(0,columns):
                ind = pattern[row][col]
                ix = devices[ind].pop()
                self.df.at[ix,"row"] = row
                self.df.at[ix,"column"] = col
                pass


        self.df = self.df.sort_values(["row","column"])

        c  = self.design.cells[self.df.at[ix,"cellName"]]

        x = self.df["x"].min()
        y = self.df["y"].min()
        for row in range(0,rows):
            self.placeHorizontal(row,x,y)
            y += self.snap(c.toMicron(c.height()))


        print(self.df)

    def placeVertical(self,column=0,x=None,y=None):

        if(x is None):
            x = self.df["x"].min()

        if(y is None):
            y = self.df["y"].min()

        for i,d in self.df.iterrows():

            if(d["column"] != column):
                continue

            if(d["cellName"] not in self.design.cells):
                continue

            c  = self.design.cells[d["cellName"]]
            self.setPos(i,c,x,y,"R0")
            x = self.snap(x)
            y += self.snap(c.toMicron(c.height()))
            pass

    def placeHorizontal(self,row=0,x=None,y=None):
        if(x is None):
            x = self.df["x"].min()

        if(y is None):
            y = self.df["y"].min()


        ind = 1
        orient = "R0"
        for i,d in self.df.iterrows():

            if(d["row"] != row):
                continue

            if(d["cellName"] not in self.design.cells):
                continue

            c  = self.design.cells[d["cellName"]]

            cname = d["cellName"]

            if(re.search("C?NCH",cname)):
                if(ind == 1):
                    orient = "R0"
                else:
                    orient = "MY"
            elif(re.search("C?PCH",cname)):
                if(ind == 1):
                    orient = "MY"
                else:
                    orient = "R0"

            trans_orient = orient
            prev_orient = self.df.at[i,"orient"]

            if(prev_orient == orient):
                trans_orient = "R0"

            if(trans_orient == "MY"):
                self.df.at[i,"x"] *= -1

            self.setPos(i,c,x,y,trans_orient)

            if(ind == 1):
                ind = -1
            else:
                ind = 1
            x += self.snap(c.toMicron(c.width()))
            y  = y


    def toCsv(self,fname):
        self.df.to_csv(fname)

    def toSkill(self,fname):

        buff= """
objs = geGetSelectedSet()
(foreach o objs
        """

        for i,d in self.df.iterrows():


            buff += f"""
        if(rexMatchp("{d.instanceName}" o~>name) then
            dbMoveFig(o nil list({d.xd}:{d.yd} "{d.orientn}"))

        )

        """
        buff += ")"
        with open(fname,"w") as fo:
            fo.write(buff)
