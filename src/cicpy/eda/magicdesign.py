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
            #- A LIBRARY CELL STARTS AT THE ORIGIN. A generated subcell
            #- keeps its parent's absolute coordinates on disk (the
            #- restructuring step owns changing that), and placing it
            #- unnormalised lands its body at placement + offset. Here
            #- the .mag has just been parsed into objects nothing else
            #- shares, so the translation that was unsafe on the live
            #- design graph is safe by construction. A no-op for every
            #- cell already drawn at the origin.
            self._lay.updateBoundingRect()
            ox, oy = int(self._lay.x1), int(self._lay.y1)
            #- the shift is DATA: the .mag on disk still starts at
            #- (ox, oy), so the painted use record must carry
            #- xcell = -ox to land the disk geometry where the model
            #- says it is. addInstance reads this off the cell.
            self._lay.libshift = (ox, oy)
            if ox or oy:
                self._lay.translate(-ox, -oy)
                self._lay.updateBoundingRect()
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
        self.primitive_cache_dir = ""

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

        #- Make top cell -- through the factory seam, so a registered
        #- cell name gets its own LayoutCell subclass
        ckt = sp[cellname]
        cell = self.newLayoutCell(cellname)
        cell.name = cellname
        cell.ckt = ckt
        cell.subckt = ckt
        cell.parent = self
        self.add(cell)
        return cell

    def getLayoutCell(self,subcktName):
        """The cell to instantiate for this subckt name.

        A CELL BUILT THIS RUN WINS over a .mag on disk, and that
        ordering is load bearing rather than cosmetic. scanLibraryPath
        globs libdir/**/*.mag, which on any rebuild includes the
        PREVIOUS run's generated subcells -- so preferring maglib would
        quietly build a parent against last run's children and only the
        timestamps would say so.

        This is also what lets a subcell be generated and used in one
        process. Until now the only way in was a .mag that existed
        before the run started, which is why the hierarchical build had
        to be two commands.
        """
        cell = self.cells.get(subcktName)
        if cell is not None:
            if subcktName in self.maglib:
                self.log.debug(
                    f"{subcktName}: built this run, shadowing "
                    f"{self.maglib[subcktName].filename}")
            return cell
        if(subcktName in self.maglib):
            return self.maglib[subcktName].getLayoutCell()
        return None
