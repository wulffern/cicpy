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

import math

class Point:

    def __init__(self,x,y):
        self.x = x
        self.y = y

    def setPoint(self,x,y):
        self.x = x
        self.y = y

    def rotate(self,org_x,org_y,angle):
        angle_ = angle*2*math.asin(1)/180.0
        self.x = math.cos(angle_)*(self.x - org_x) - math.sin(angle_)*(self.y - org_y) + org_x
        self.y = math.sin(angle_) *(self.y - org_x) + math.cos(angle_) * (self.y- org_y) + org_y

    def translate(self,dx,dy):
        self.x = self.x + dx
        self.y = self.y + dx

    def leftOf(self,point):
        if(point.x < self.x):
            return True
        return False

    def over(self,point):
        if(point.y > self.y):
            return True
        return False

    def swapX(self,x2):
        xx = self.x
        self.x = x2
        return xx

    def swapY(self,y2):
        self.y = y2
        return self.y

    def __str__(self):
        s = "x=%d, y=%d" %(self.x,self.y)
        return s

    def __eq__(self, point):
        if(point.x == self.x and point.y == self.y):
            return True
        return False

