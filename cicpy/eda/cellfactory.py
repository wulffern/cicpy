#!/usr/bin/env python3

import cicpy as cic
import os
import re

cells = dict()
subcells = dict()

def getCellFromSymbol(libdir,symbol):
    path = libdir + symbol.replace(".sym",".mag")
    if(not os.path.exists(path)):
        raise Exception("Could not find %s" %(path))

    if("path" not in cells):
        lay = cic.eda.Layout()
        lay.readFromFile(path)
        cells[path] = lay
    return cells[path]

def getLayoutCellFromSchCell(libdir,schCell):
    names = schCell.name().split("_")

    layName = libdir + schCell.symbol.replace(".sym",".mag")

    lcell = cic.Layout()
#    print(layName)
    lcell.readFromFile(layName)
    #lcell.updateBoundingRect()

    #print(names)
 #   print(lcell)


    #raise Exception("Figure out to organize subcells")
    #- Should not return
    return lcell

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

def getLayoutCellFromXSch(libdir,xs,xspace,yspace,gbreak):

    root = cic.eda.Layout()
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

    print(next_xspace)
    print(next_yspace)

    next_x = 0
    next_y = 0

    prevgroup = ""

    ymax = 0
    yorg = 0
    xorg = 0
    groupcount = 0
    first = True

    for instanceName in xs.orderByGroup():

        scell = xs.components[instanceName]

        #- TODO: Figure out how to handle ports
        if("devices/" in scell.symbol):
            continue

        #- Categorise based on name <ident>_<ident>_<nr>

        #raise Exception("Figure out how to organize subcells")

        lcell = getLayoutCellFromSchCell(libdir,scell)


        name = scell.name()
        group = scell.group()

        if(group != prevgroup or prevgroup == ""):
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

        (next_x,next_y) = placeACell(root,lcell,scell,name,x,y)

        if(next_y > ymax):
            ymax = next_y

        x = lcell.x1
        y = next_y

        prevgroup = group
        first = False


    root.updateBoundingRect()

    return root
