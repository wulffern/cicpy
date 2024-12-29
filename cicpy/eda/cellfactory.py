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

def getLayoutCellFromXSch(libdir,xs):

    root = cic.eda.Layout()
    root.name = xs.name
    root.dirname = xs.dirname

    y = 0
    x = 0

    next_x = 0
    next_y = 0

    prevgroup = ""

    for instanceName in xs.orderByGroup():

        scell = xs.components[instanceName]

        #- TODO: Figure out how to handle ports
        if("devices/" in scell.symbol):
            continue

        #- Categorise based on name <ident>_<ident>_<nr>

        #raise Exception("Figure out how to organize subcells")

        lcell = getLayoutCellFromSchCell(libdir,scell)

        print(lcell)

        name = scell.name()
        group = scell.group()

        if(group != prevgroup or prevgroup == ""):
            y = 0
            x = next_x

        (next_x,next_y) = placeACell(root,lcell,scell,name,x,y)

        x = lcell.x1
        y = next_y

        prevgroup = group


    root.updateBoundingRect()

    return root
