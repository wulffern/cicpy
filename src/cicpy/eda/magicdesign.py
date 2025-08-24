#!/usr/bin/env python3

import cicpy as cic
import cicspi
import glob
import os
import re

class MagicFile():
    def __init__(self,filename,parent):
        self.filename = filename
        self.name = os.path.basename(filename).replace(".mag","")
        self.dirname = os.path.dirname(filename)
        self.libname = os.path.basename(self.dirname)
        self.parent = parent
        self._lay = None
        self.top = None
        self.bot = None
        pass

    def loadLayoutCell(self):
        if(self._lay is None):
            self._lay = cic.Layout(self.parent.techlib)
            self._lay.readFromFile(self.filename)
            if(re.search(r"CH_\d+C\d+F\d+",self.name)):
                topName = re.sub(r"C\d+F\d+","CTAPTOP",self.filename)
                if(os.path.exists(topName)):
                    self.top = cic.Layout(self.parent.techlib)
                    self.top.readFromFile(topName)
                    botName = re.sub(r"C\d+F\d+","CTAPBOT",self.filename)
                if(os.path.exists(botName)):
                    self.bot = cic.Layout(self.parent.techlib)
                    self.bot.readFromFile(botName)
        return self._lay

    def getInstance(self,cktInst):
        layoutCell = self.loadLayoutCell()
        i = cic.Instance()
        i.instanceName = cktInst.name
        i.name = cktInst.name
        i.cell = layoutCell.name
        i.layoutcell = layoutCell
        i.libpath = layoutCell.libpath
        i.updateBoundingRect()
        return i

    def getInstanceDummyBottom(self,cktInst):
        if(self.bot is None):
            return None
        i = cic.Instance()
        i.instanceName = cktInst.name + "_BOT"
        i.name = cktInst.name + "_BOT"
        i.cell = self.bot.name
        i.layoutcell = self.bot
        i.libpath = self.bot.libpath
        i.updateBoundingRect()
        return i

    def getInstanceDummyTop(self,cktInst):
        if(self.top is None):
            return None
        i = cic.Instance()
        i.instanceName = cktInst.name + "_TOP"
        i.name = cktInst.name + "_TOP"
        i.cell = self.top.name
        i.layoutcell = self.top
        i.libpath = self.top.libpath
        i.updateBoundingRect()
        return i


class MagicDesign(cic.Design):
    def __init__(self,techlib,rules):
        super().__init__()
        self.maglib = dict()
        self.rules = rules
        self.techlib = techlib

    def scanLibraryPath(self,libdir):
        files = glob.glob(libdir + "**/*mag")
        for f in files:
            m = MagicFile(f,self)
            self.maglib[m.name] = m

    def readFromSpice(self,filename,cellname):
        sp = cicspi.SpiceParser()
        sp.parseFile(filename)
        if(cellname not in sp):
            print(f"Could not find {cellname} in {str(sp.keys())}")
            return

        #- Make top cell
        ckt = sp[cellname]
        cell = cic.LayoutCell()
        cell.name = cellname
        cell.ckt = ckt
        cell.parent = self
        self.add(cell)
        return cell

    def getInstance(self,cktinst):
        cell = None
        if(cktinst.subcktName in self.maglib):
            cell = self.maglib[cktinst.subcktName].getInstance(cktinst)

        return cell

    def getInstanceDummyBottom(self,cktinst):
        cell = None
        if(cktinst.subcktName in self.maglib):
            cell = self.maglib[cktinst.subcktName].getInstanceDummyBottom(cktinst)
        return cell

    def getInstanceDummyTop(self,cktinst):
        cell = None
        if(cktinst.subcktName in self.maglib):
            cell = self.maglib[cktinst.subcktName].getInstanceDummyTop(cktinst)
        return cell
