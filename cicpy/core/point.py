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

    def __eq__(self, point):
        if(point.x == self.x and point.y == self.y):
            return True
        return False

