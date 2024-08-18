#!/usr/bin/env python3

from .subckt import Subckt
import re

class SpiceParser():

    def __init__(self):

        self.ckts = dict()


    def parseSubckt(self,lineNumber,sbuffer):
        s = Subckt()
        s.parse(lineNumber,sbuffer)
        self.ckts[s.name] =s


    def parseFile(self,fname):

        rePlus = "^\s*\+"
        reSubcktStart = "^\s*.subckt"
        reSubcktEnd = "^\s*.ends"

        isSubckt = False

        lineNumber = 0

        with open(fname) as fi:
            sbuffer = list()
            for line in fi:
                line = line.strip()

                lineNumber +=1

                #Handle plus
                if(re.search(rePlus,line)):
                    l = re.sub(rePlus,"",line)
                    sbuffer[-1] = sbuffer[-1] + l
                    continue

                #Capture start of subckt
                if(re.search(reSubcktStart,line,flags=re.IGNORECASE)):
                    isSubckt = True
                    sbuffer.clear()

                if(isSubckt):
                    sbuffer.append(line)

                if(re.search(reSubcktEnd,line,flags=re.IGNORECASE)):
                    isSubckt = False
                    self.parseSubckt(lineNumber,sbuffer)
