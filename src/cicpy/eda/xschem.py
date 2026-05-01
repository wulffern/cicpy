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

    def parseProperties(self,ss):
        if(ss is None or re.search(r"^\s*$",ss)):
            return
        ss = re.sub(r"\n"," ",ss).strip()
        key_value_pairs = re.findall(r'(?:[^\s"]|"(?:\\.|[^"])*")+',ss)
        for s in key_value_pairs:
            if(re.search(r"^\s*$",s)):
                continue
            ar = s.split("=",1)
            if(len(ar) != 2):
                # Bare flag (no =) — keep as boolean true
                self.properties[s] = True
                continue
            (key,val) = ar
            self.properties[key] = val

    def isType(self,typename):
        if(self.__class__.__name__ == typename):
            return True
        elif(super() and (super().__class__.__name__ == typename)):
            return True
        return False


# Generic regex helpers for lines like "<C> f1 f2 ... fN [{props}]" where the
# first character has already been consumed and only the body of the line is
# matched. Property block may span multiple lines (re.S).
def _shape_pattern(n_fields):
    return re.compile(
        r"^\s+" + r"\s+".join([r"(\S+)"] * n_fields) + r"(?:\s+\{(.*)\})?\s*$",
        re.S,
    )


_LINE_RE = _shape_pattern(5)   # color x1 y1 x2 y2
_RECT_RE = _shape_pattern(5)   # color x1 y1 x2 y2  (used for B too)
_ARC_RE  = _shape_pattern(6)   # color x y r start sweep
_WIRE_RE = _shape_pattern(4)   # x1 y1 x2 y2 (no color)
# Text: T {text body} x y rot flip xscale yscale [{props}]
_TEXT_RE = re.compile(
    r"^\s*T\s+\{(.*?)\}\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)"
    r"(?:\s+\{(.*)\})?\s*$",
    re.S,
)
_POLY_PREFIX_RE = re.compile(r"^\s+(\S+)\s+(\d+)\s+(.*)$", re.S)



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

class GlobalFormat(Object):
    pass

class Line(Object):
    def parse(self, ss):
        super().parse(ss)
        body = ss[1:]  # drop leading 'L'
        m = _LINE_RE.match(body)
        if not m:
            raise Exception(f"Could not parse Line: {ss!r}")
        self.color = int(m.group(1))
        self.x1 = float(m.group(2))
        self.y1 = float(m.group(3))
        self.x2 = float(m.group(4))
        self.y2 = float(m.group(5))
        self.parseProperties(m.group(6))


class Rect(Object):
    def parse(self, ss):
        super().parse(ss)
        body = ss[1:]  # drop leading 'B'
        m = _RECT_RE.match(body)
        if not m:
            raise Exception(f"Could not parse Rect: {ss!r}")
        self.color = int(m.group(1))
        self.x1 = float(m.group(2))
        self.y1 = float(m.group(3))
        self.x2 = float(m.group(4))
        self.y2 = float(m.group(5))
        self.parseProperties(m.group(6))


class Polygon(Object):
    def parse(self, ss):
        super().parse(ss)
        body = ss[1:]  # drop leading 'P'
        m = _POLY_PREFIX_RE.match(body)
        if not m:
            raise Exception(f"Could not parse Polygon: {ss!r}")
        self.color = int(m.group(1))
        n = int(m.group(2))
        rest = m.group(3).strip()
        # Split off optional trailing {props}
        props = None
        if rest.endswith("}"):
            brace = rest.rfind("{")
            if brace >= 0:
                props = rest[brace + 1:-1]
                rest = rest[:brace].strip()
        tokens = rest.split()
        coords = [float(t) for t in tokens[: 2 * n]]
        self.points = list(zip(coords[0::2], coords[1::2]))
        self.parseProperties(props)


class Arc(Object):
    def parse(self, ss):
        super().parse(ss)
        body = ss[1:]  # drop leading 'A'
        m = _ARC_RE.match(body)
        if not m:
            raise Exception(f"Could not parse Arc: {ss!r}")
        self.color = int(m.group(1))
        self.x = float(m.group(2))
        self.y = float(m.group(3))
        self.r = float(m.group(4))
        self.start_angle = float(m.group(5))
        self.sweep_angle = float(m.group(6))
        self.parseProperties(m.group(7))


class Text(Object):
    def parse(self, ss):
        super().parse(ss)
        m = _TEXT_RE.match(ss)
        if not m:
            raise Exception(f"Could not parse Text: {ss!r}")
        self.text = m.group(1)
        self.x = float(m.group(2))
        self.y = float(m.group(3))
        self.rotation = int(m.group(4))
        self.flip = int(m.group(5))
        self.xscale = float(m.group(6))
        self.yscale = float(m.group(7))
        self.parseProperties(m.group(8))


class Wire(Object):
    def parse(self, ss):
        super().parse(ss)
        body = ss[1:]  # drop leading 'N'
        m = _WIRE_RE.match(body)
        if not m:
            raise Exception(f"Could not parse Wire: {ss!r}")
        self.x1 = float(m.group(1))
        self.y1 = float(m.group(2))
        self.x2 = float(m.group(3))
        self.y2 = float(m.group(4))
        self.parseProperties(m.group(5))

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
        elif(c == "F"):
            o = GlobalFormat()
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
