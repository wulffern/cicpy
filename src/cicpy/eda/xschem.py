#!/usr/bin/env python3
######################################################################
##        Copyright (c) 2025 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2025-3-27
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################

import re
import logging
import os

class Object():
    def __init__(self):
        self.properties = dict()
        pass

    def parse(self,ss):
        self.ss = ss

    def property(self,key,val=None):
        if(key in self.properties):
            if(val):
                self.properties[key] = cal
            return self.properties[key]
        else:
            return None

    def isType(self,typename):
        if(self.__class__.__name__ == typename):
            return True
        elif(super() and (super().__class__.__name__ == typename)):
            return True
        return False



class Version(Object):
    pass

class GlobalSpice(Object):
    pass

class GlobalVerilog(Object):
    pass

class GlobalVHDL(Object):
    pass

class GlobalTEDA(Object):
    pass

class GlobalProperties(Object):
    pass

class Line(Object):
    pass

class Rect(Object):
    pass

class Polygon(Object):
    pass

class Arc(Object):
    pass

class Text(Object):
    pass

class Wire(Object):
    pass

class Component(Object):

    def __init__(self):
        super().__init__()
        self.symbol = None
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.flip = 0


    def parseProperties(self,ss):
        if(re.search(r"^\s*$",ss)):
            return

        ss = re.sub(r"\n"," ",ss).strip()

        key_value_pairs = re.findall(r'(?:[^\s"]|"(?:\\.|[^"])*")+',ss)
        for s in key_value_pairs:
            if(re.search(r"^\s*$",s)):
                continue
            ar = re.split("=",s)
            if(len(ar) != 2):

                raise Exception("Don't know how to parse %s" %(ar))
                continue
            (key,val) = ar
            self.properties[key] = val


    def name(self,val = None):
        return self.property("name",val)

    def group(self):
        name = self.name()
        m = re.search(r"^(x\D+)",name,re.I)
        if(m is not None):
            group = m.groups(0)[0]
        else:
            group = ""
        return group

    def parse(self,ss):
        super().parse(ss)
        m = re.search(r"C {([^}]+)} (\S+) (\S+) (\S+) (\S+) {([^}]*)}",ss,re.MULTILINE)

        if(m):
            ar = m.groups()
            self.symbol = ar[0]
            self.x = ar[1]
            self.y = ar[2]
            self.rotation = ar[3]
            self.flip = ar[4]
            self.parseProperties(ar[5])
        else:
            raise Exception("Could not parse Component %s "%ss)
        #print(ss)
    pass

class EmbedSymbol(Object):
    pass


class XSchem():

    def __init__(self):
        self.children = list()
        self.components = dict()
        self.name = ""
        self.path = ""
        self.log = logging.getLogger("XSchem")
        pass

    def getPorts(self):
        ports = list()
        for instName in self.components:

            if(re.search("^p",instName,re.I)):
                ports.append(self.components[instName])
        return ports

    def orderByGroup(self):

        instList = list()
        groups = dict()
        for instName in sorted(self.components):

            c = self.components[instName]
            if( re.search("^(p|l)",instName,re.I)):
                continue
            #Ignore anything that does not start with X or x
            if(not re.search("^x",instName,re.I)):
                self.log.info(f"Don't know how to layout {instName}.")
                continue

            group = c.group()
            if(group not in groups):
                groups[group] = list()
            groups[group].append(instName)


        for g in sorted(groups):
            arr = sorted(groups[g])
            instList += arr

        return instList

    
    def countPattern(self,pattern,line):
        count = len(re.findall("("+pattern+")",line))
        return count

    def parseBuffer(self,buff):

        c = buff[0]
        o = None
        if(c == "v"):
            o = Version()
        elif(c == "S"):
            o = GlobalSpice()
        elif(c == "V"):
            o = GlobalVerilog()
        elif(c == "G"):
            o = GlobalVHDL()
        elif(c == "E"):
            o = GlobalTEDA()
        elif(c == "K"):
            o = GlobalProperties()
        elif(c == "L"):
            o = Line()
        elif(c == "B"):
            o = Rect()
        elif(c == "P"):
            o = Polygon()
        elif(c == "A"):
            o = Arc()
        elif(c == "T"):
            o = Text()
        elif(c == "N"):
            o = Wire()
        elif(c == "C"):
            o = Component()
        elif(c == "["):
            o = EmbedSymbol()
        else:
            self.log.warning(f"Unknown property {c}" + " on " + buff)


        if(o is not None):
            o.parse(buff)
            self.children.append(o)


    
    def readFromFile(self,fname):

        self.name = os.path.basename(fname).replace(".sch","")
        self.dirname = os.path.dirname(fname)

        with open(fname) as fi:
            buff = ""
            pcount = 0
            ind =0
            for line in fi:
                ind += 1

                #- Check for symbol embedding
                if(re.search(r"^\[",line)):
                    raise Exception("Symbol Embedding on line %d not supported" % ind)

                #- Gobble up all {} with a stack
                start_p =self.countPattern("{",line)
                stop_p =self.countPattern("}",line)
                pcount += start_p - stop_p

                buff += line

                if(pcount == 0):
                    self.parseBuffer(buff)
                    buff = ""

        for c in self.children:
            if(c.isType("Component")):

                instanceName = c.name()
                if(instanceName):
                    self.components[instanceName] = c

    def toYaml(self):
        data = dict()

        for (key,o) in self.components.items():
            raise Exception("How should the yaml look???")
                

class Schematic(XSchem):

    def fromFile(fname):
        x = Schematic()
        x.readFromFile(fname)
        return x
    pass

class Symbol(XSchem):

    def fromFile(fname):
        x = Symbol()
        x.readFromFile(fname)
        return x
    pass
