######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-14
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
import json
import sys
from .point import Point

INT_MAX = sys.maxsize  
INT_MIN = -sys.maxsize-1
    
def sortOnTop(rects,left=False,right=False,top=False,bottom=False):
    if(len(rects)<2):
        return rects
    index = 0
    count = 0

    x =  INT_MAX
    y = INT_MAX
    if(right):
        x = INT_MIN
    elif(bottom):
        y = INT_MIN

    for r in rects:
        if(left and r.x1 < x):
            index = count
            x = r.x1
        elif(right and r.x2 > x):
            index = count
            x = r.x2
        elif(bottom and r.y1 < y):
            index = count
            y = r.y1
        elif(top and r.y2 > y):
            index = count
            y = r.y2
        count +=1
    a = rects[0]
    rects[0] = rects[index]

def sortLeftOnTop(rects):
    sortOnTop(rects,left=True)

def sortRightOnTop(rects):
    sortOnTop(rects,right=True)

def sortBottomOnTop(rects):
    sortOnTop(rects,bottom=True)

def sortTopOnTop(rects):
    sortOnTop(rects,top=True)


def Scaled(rect,unit):
    r = Rect("",rect.x1/unit,rect.y1/unit,0,0)
    r.setPoint2(rect.x2/unit,rect.y2/unit)
    r.layer = rect.layer
    r.net = rect.net

def snap(x):
    GRID = 5
    x = int(x/GRID)*GRID
    return x

def HorizontalRectangleFromTo(self, layer,  x1,  x2,  y,  height):
    if(x1 > x2):
        r = Rect(layer,x2,y,x1-x2,height)
    else:
        r = Rect(layer,x1,y,x2-x1,height)
    return r


def VerticalRectangleFromTo(layer, x, y1, y2, width):
    if(y1 > y2):
        r = Rect(layer,x,y2,width,y1-y2)
    else:
        r = Rect(layer,x,y1,width,y2-y1)
    return r

#----------------------------------------------------------------
# Rectangle
#----------------------------------------------------------------
class Rect:

    def __init__(self,layer="",x=0,y=0,width=0,height=0):

        if(width < 0):
            self.x1 = x + width
            self.x2 = x
        else:
            self.x1 = x
            self.x2 = x + width

        if(height < 0):
            self.y1 = y + height
            self.y2 = y
        else:
            self.y1 = y
            self.y2 = y + height
        self.layer = layer
        self.parent = None
        self.net = ""
        self.classname = "Rect"
        self.listeners = list()
    
    def setPoint1(self,x1,y1):
        self.x1 = x1
        self.y1 = y1

    def setPoint2(self,x2,y2):
        self.x2 = x2
        self.y2 = y2
    
    def setRect(self,r):
        self.x1 = r.x1
        self.y1 = r.y1
        self.x2 = r.x2
        self.y2 = r.y2

    def connect(self,fp):
        self.listeners.append(fp)

    def emit_updated(self):
        for fp in self.listeners:
            fp()
        pass

    def left(self):
        return self.x1
    
    def right(self):
        return self.x2

    def top(self):
        return self.y2
    
    def bottom(self):
        return self.y1

    def width(self):
        return self.x2 - self.x1

    def height(self):
        return self.y2 - self.y1

    def centerX(self):
        return self.x1 + self.width()/2

    def centerY(self):
        return self.y1  + self.height()/2

    def moveTo(self,x,y):
        w = self.width()
        h = self.height()
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
        self.emit_updated()

    def moveCenter(self,xc,yc):
        w = self.width()
        h = self.height()
        self.x1 = xc - w/2
        self.y1 = yc - h/2
        self.x2 = self.x1 + w
        self.y2 = self.y1 + h
        self.emit_updated()

    def empty(self):
        if (self.x1 == self.x2 or self.y1 == self.y2):
            return True
        return False

    def adjust(self,dx):
        self.x1 -= dx
        self.y1 -= dx
        self.x2 += dx
        self.y2 += dx

    def translate(self,ax,ay):
        self.x2 += ax
        self.x1 += ax
        self.y1 += ay
        self.y2 += ay
        self.emit_updated()

    def isHorizontal(self):
        if(self.width >= self.height):
            return True
        return False
    
    def isVertical(self):
        if(self.height >= self.width):
            return True
        return False    
    
    def setParent(self,rect):
        self.parent = rect
        return rect
    
    def setNet(self,net):
        self.net = net

    def getCopy(self):
        r = Rect(self.layer,self.x1,self.y1,self.width(),self.height())
        r.setNet(self.net)
        return r

    def CopyToLayer(self,layer):
        r = self.getCopy()
        r.layer = layer
        return r

    def rotate(self,i):
        p1 = Point(self.x1,self.y1)
        p2 = Point(self.x2,self.y2)
        p1.rotate(0,0,i)
        p2.rotate(0,0,i)

        if(p2.x < p1.x):
            xx = p1.x
            p1.x = p2.x
            p2.x = xx

        if(p2.y < p1.y):
            yy = p1.y
            p1.y = p2.y
            p2.y = yy
        self.x1 = p1.x
        self.x2 = p2.x
        self.y1 = p1.y
        self.y2 = p2.y
        self.emit_updated()

    def adjustedOnce(self,xp1):
        rect = Rect(self.layer,self.x1 - xp1, self.y1- xp1, self.width + 2*xp1, self.height + 2*xp1)
        return rect

    def mirrorY(self,ax):
        self.setLeft(2.0*ax - self.left())
        self.setRight(2.0*ax - self.right())

        #Flip left and right if width is negative
        if (self.width() < 0  ):
            tmp = self.left()
            self.setLeft(self.right())
            self.setRight(tmp)
        
        self.emit_updated()
    


    def mirrorX(self,ay):
        self.setTop(2 *  ay - self.top())
        self.setBottom(2 *  ay - self.bottom())

        #Flip top and bottom if height is negative
        if (self.height() < 0):
            tmp = self.top()
            self.setTop(self.bottom())
            self.setBottom(tmp)
        self.emit_updated()

    def abutsLeft(self,r):
        if(self.x2 == r.x1 and self.y1 == r.y1 and self.y2 == r.y2):
            return True
        return False


    def abutsRight(self,r):
        if(self.x1 == r.x2 and self.y1 == r.y1 and self.y2 == r.y2):
            return True    
        return False

    def abutsTop(self,r):
        if(self.x1 == r.x1 and self.y2 == r.y1 and self.x2 == r.x2):
            return True
        return False

    def abutsBottom(self,r):
        if(self.x1 == r.x1 and self.y1 == r.y2 and self.x2 == r.x2):
            return True
        return False

    def __str__(self):
        return "%s: layer=%s X=%d Y=%d W=%d H=%d" %(self.__class__,self.layer,self.x1,self.y1,self.width(),self.height())

    def fromJson(self,o):
        self.x1 = o["x1"]
        self.x2 = o["x2"]
        self.y1 = o["y1"]
        self.y2 = o["y2"]
        self.layer = o["layer"]
        self.net = o["net"]
        self.classname = o["class"]

    def toJson(self):
        o = dict()
        o["class"] = "Rect"
        o["x1"] = self.x1
        o["y1"] = self.y1
        o["x2"] = self.x2
        o["y2"] = self.y2
        o["layer"] = self.layer
        o["net"] = self.net
        return o


    def printToJson(self):
        print(json.dumps(self.toJson(),indent=4))

    def isType(self,typename):
        if(self.__class__.__name__ == typename):
            return True
        elif(super() and (super().__class__.__name__ == typename)):
            return True
        return False

    def isInstance(self):
        return self.isType("Instance")

    def isRect(self):
        return self.isType("Rect")

    def isPort(self):
        return self.isType("Port")

    def isRoute(self):
        return self.isType("Route")

    def isCut(self):
        return self.isType("Cut")

    def isCell(self):
        return self.isType("Cell")

    def isLayoutCell(self):
        return self.isType("LayoutCell")

    def isRoute(self):
        return self.isType("Route")

    def isText(self):
        return self.isType("Text")


    
    
