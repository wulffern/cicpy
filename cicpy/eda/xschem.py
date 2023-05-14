#!/usr/bin/env python3
#
import re

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
        if(re.search("^\s*$",ss)):
            return
        kval = re.split("\s",ss,re.MULTILINE)
        for s in kval:
            (key,val) = s.split("=")
            self.properties[key] = val


    def name(self,val = None):
        return self.property("name",val)

    def parse(self,ss):
        super().parse(ss)
        m = re.search("C {([^}]+)} (\S+) (\S+) (\S+) (\S+) {([^}]*)}",ss,re.MULTILINE)

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
        self.components = list()
        pass

    def countPattern(self,pattern,line):
        m = re.search("("+pattern+")",line)
        count = 0
        if(m):
            count = len(m.groups())
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
            self.components.append(o)
        elif(c == "["):
            o = EmbedSymbol()

        o.parse(buff)
        self.children.append(o)


    
    def readFromFile(self,fname):
        with open(fname) as fi:
            buff = ""
            pcount = 0
            ind =0
            for line in fi:
                ind += 1

                #- Check for symbol embedding
                if(re.search("^\[",line)):
                    raise Exception("Symbol Embedding on line %d not supported" % ind)

                #- Gobble up all {} with a stack
                start_p =self.countPattern("{",line)
                stop_p =self.countPattern("}",line)
                pcount += start_p - stop_p

                buff += line

                if(pcount == 0):
                    self.parseBuffer(buff)
                    buff = ""



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