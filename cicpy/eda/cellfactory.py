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

import cicpy as cic
import os
import re

cells = dict()
lcells = dict()
subcells = dict()
tops = dict()
bots = dict()

def getCellFromSymbol(libdir,symbol):
    path = libdir + symbol.replace(".sym",".mag")
    if(not os.path.exists(path)):
        raise Exception("Could not find %s" %(path))

    if("path" not in cells):
        lay = cic.eda.Layout()
        lay.readFromFile(path)
        cells[path] = lay
    return cells[path]

def getLayoutCellFromSchCell(libdir,schCell,techlib):
    names = schCell.name().split("_")

    layName = libdir + schCell.symbol.replace(".sym",".mag")
    if(layName not in lcells):
        lcell = cic.Layout(techlib)
        lcell.readFromFile(layName)
        lcells[layName] = lcell
        if(re.search(r"CH_\d+C\d+F\d+",layName)):
            topName = re.sub(r"C\d+F\d+","CTAPTOP",layName)
            if(os.path.exists(topName)):
                top = cic.Layout(techlib)
                top.readFromFile(topName)
                tops[lcell.name] = top
            botName = re.sub(r"C\d+F\d+","CTAPBOT",layName)
            if(os.path.exists(botName)):
                bot = cic.Layout(techlib)
                bot.readFromFile(botName)
                bots[lcell.name] = bot

    #raise Exception("Figure out to organize subcells")
    #- Should not return
    return lcells[layName]

def getInstanceFromComponent(layoutCell,component,x,y):
    i = cic.Instance()
    i.instanceName = component.name()
    i.name = component.name()
    i.cell = layoutCell.name
    i.layoutcell = layoutCell
    i.libpath = layoutCell.libpath
    i.moveTo(x,y)
    i.updateBoundingRect()
    
    return i

count = 0
def placeDummy(root,lcell,x,y):
    global count
    i = cic.Instance()
    i.instanceName = "X" + lcell.name + str(count)
    i.name = lcell.name
    i.cell = lcell.name
    i.layoutcell = lcell
    i.libpath = lcell.libpath
    i.moveTo(x,y)
    i.updateBoundingRect()
    root.add(i)
    count +=1
    return i

def placeACell(root,lcell,scell,name,x,y):
    next_x = 0
    next_y = 0
    match = re.findall(r"\[(\d+:\d+)\]",name)
    if(match): #- Multiple instances
        ly = y
        lx = 0
        local_cell = cic.core.LayoutCell()

        if(len(match) > 1):
            raise Exception("Name contains duplicate [d:d] %s"%str(match))
        #- Assume 1 match, anything else is an error
        (end,start) = re.split(":",match[0])
        for i in range(int(start),int(end)+1):
            i = getInstanceFromComponent(lcell,scell,x,ly)
            local_cell.add(i)
            ly += lcell.height()
            next_x = i.x2
            next_y = i.y2

        root.add(local_cell)

    else: #- Single instance
        i = getInstanceFromComponent(lcell,scell,x,y)
        root.add(i)
        next_x = i.x2
        next_y = i.y2

    return (next_x,next_y)

def getLayoutCellFromXSch(libdir,xs,xspace,yspace,gbreak,techlib):

    root = cic.eda.Layout(techlib)
    root.name = xs.name
    root.dirname = xs.dirname

    y = 0
    x = 0

    gbreaks = gbreak.split(",")
    if(type(gbreaks) == list):
        next_gbreak = int(gbreaks.pop())
    else:
        next_gbreak = int(gbreak)


    xps = xspace.split(",")
    if(type(xps) == list):
        next_xspace = int(xps.pop())
    else:
        next_xspace = int(xspace)

    yps = yspace.split(",")
    if(type(yps) == list):
        next_yspace = int(yps.pop())
    else:
        next_yspace = int(yspace)

    next_x = 0
    next_y = 0

    prevgroup = ""

    ymax = 0
    yorg = 0
    xorg = 0
    groupcount = 0
    first = True
    startGroup = False
    endGroup = False
    prevcell = None

    for instanceName in xs.orderByGroup():

        scell = xs.components[instanceName]

        #- TODO: Figure out how to handle ports
        if("devices/" in scell.symbol):
            continue

        #- Categorise based on name <ident>_<ident>_<nr>

        #raise Exception("Figure out how to organize subcells")

        lcell = getLayoutCellFromSchCell(libdir,scell,techlib)

        #design.add(lcell)
        name = scell.name()
        group = scell.group()

        if(group != prevgroup or prevgroup == ""):
            startGroup = True

            if(prevcell is not None and prevcell.name in tops):
                i = placeDummy(root,tops[prevcell.name],x,y)
                x = i.x1
                y = i.y2
                next_y = y
                if(next_y > ymax):
                    ymax = next_y


            if(next_gbreak == groupcount):
                y = ymax + next_yspace
                yorg = y
                if(type(gbreak) == list):
                    next_gbreak = int(gbreak.pop())
                x = 0
            else:
                y = yorg

                if(first):
                    x = 0
                else:
                    x = next_x + next_xspace
                    if(type(xps) == list and len(xps) > 0):
                        next_xspace = int(xps.pop())

            groupcount += 1

        if(startGroup):
            if(lcell.name in bots):
                i= placeDummy(root,bots[lcell.name],x,y)
                x = i.x1
                y = i.y2


        (next_x,next_y) = placeACell(root,lcell,scell,name,x,y)

        if(next_y > ymax):
            ymax = next_y

        x = lcell.x1
        y = next_y

        prevcell = lcell

        prevgroup = group
        first = False
        startGroup = False

    if(prevcell is not None and prevcell.name in tops):
        i = placeDummy(root,tops[prevcell.name],x,y)
        x = i.x1
        y = i.y2
        next_y = y


    root.updateBoundingRect()

    return root
