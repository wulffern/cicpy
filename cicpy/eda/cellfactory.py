#!/usr/bin/env python3

import cicpy as cic
import os

cells = dict()

def getCell(libdir,symbol):
    path = libdir + symbol.replace(".sym",".mag")
    if(not os.path.exists(path)):
        raise Exception("Could not find %s" %(path))

    if("path" not in cells):
        lay = cic.eda.Layout()
        lay.readFromFile(path)
        cells[path] = lay
    return cells[path]


def getLayoutCellFromXSch(libdir,xs):


    lc = cic.eda.Layout()
    lc.name = xs.name
    lc.dirname = xs.dirname

    y = 0
    x = 0
    for s in xs.components:
        c = xs.components[s]
        #- Skip basic instances
        #- TODO: Figure out how to handle ports
        if("devices/" in c.symbol):
            continue

        cl = getCell(libdir,c.symbol)
        i = cic.Instance()
        i.instanceName = c.name()
        i.name = c.name()
        i.cell = cl.name
        i.libpath = cl.libpath
        i.xcell = x
        i.ycell = y
        lc.add(i)
        x += cl.width()

    lc.updateBoundingRect()

    return lc
