#!/usr/bin/env python3

import cicpy as cic
import cicspi
import glob
import os
import re
import logging

class MagicFile():
    def __init__(self,filename,parent):
        self.filename = filename
        self.name = os.path.basename(filename).replace(".mag","")
        self.dirname = os.path.dirname(filename)
        self.libname = os.path.basename(self.dirname)
        self.parent = parent
        self._lay = None

        pass

    def loadLayoutCell(self):
        if(self._lay is None):
            self._lay = cic.Layout(self.parent.techlib)
            self._lay.readFromFile(self.filename)
#            if(re.search(r"CH_\d+C\d+F\d+",self.name)):
#                topName = re.sub(r"C\d+F\d+","CTAPTOP",self.filename)
#                if(os.path.exists(topName)):
#                    self.top = cic.Layout(self.parent.techlib)
#                    self.top.readFromFile(topName)
#                    botName = re.sub(r"C\d+F\d+","CTAPBOT",self.filename)
#                if(os.path.exists(botName)):
#                    self.bot = cic.Layout(self.parent.techlib)
#                    self.bot.readFromFile(botName)
        return self._lay


    def getLayoutCell(self):
        return self.loadLayoutCell()

class MagicDesign(cic.Design):
    def __init__(self,techlib,rules):
        super().__init__()
        self.maglib = dict()
        self.rules = rules
        self.techlib = techlib
        self.log = logging.getLogger("MagicDesign")

    def scanLibraryPath(self,libdir):
        files = glob.glob(libdir + "**/*mag")
        for f in files:
            m = MagicFile(f,self)
            self.maglib[m.name] = m

    def readFromSpice(self,filename,cellname):
        sp = cicspi.SpiceParser()
        sp.parseFile(filename)
        if(cellname not in sp):
            self.log.warning(f"Could not find {cellname} in {str(sp.keys())}")
            return

        #- Make top cell
        ckt = sp[cellname]
        cell = cic.LayoutCell()
        cell.name = cellname
        cell.ckt = ckt
        cell.subckt = ckt
        cell.parent = self
        self.add(cell)
        return cell

    def getLayoutCell(self,subcktName):
        cell = None
        if(subcktName in self.maglib):
            cell = self.maglib[subcktName].getLayoutCell()
        return cell
