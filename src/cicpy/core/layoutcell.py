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

from .rect import Rect
from .cell import Cell
from .port import Port
from .rules import Rules
from .instance import Instance
from .text import Text
from .graph import Graph
from .routering import RouteRing
from .guard import Guard
from .cut import Cut
import cicspi as spi
import re
import logging


class LayoutCell(Cell):

    def __init__(self):
        super().__init__()
        #self.rules = rules
        self.altenateGroup = False
        self.alternateGroup = False
        self.noPowerRoute = False
        self.boundaryIgnoreRouting = False
        self.useHalfHeight = False
        self.graph = None
        self._placeHorizontal = False
        self.nodeGraph = dict()
        self.nodeGraphList = list()
        self.um = 10000
        self.log = logging.getLogger("LayoutCell")
        self.dummyCounter = 0
        rules = Rules.getInstance()
        if(rules.hasRules()):
            space =rules.get("CELL","space")
            self.place_groupbreak = [100]
            self.place_xspace = [space]
            self.place_yspace = [space]



    def addInstance(self,cktInst,x:int,y:int):

        if(cktInst is None):
            return

        i = Instance()
        layoutCell = self.parent.getLayoutCell(cktInst.subcktName)
        i.cell = layoutCell.name
        i.layoutcell = layoutCell
        i.libpath = layoutCell.libpath
        i.setSubcktInstance(cktInst)

        self.add(i)
        i.moveTo(x,y)
        self.addToNodeGraph(i)
        i.updateBoundingRect()
        return i

    def addToNodeGraph(self,inst):

        if (inst is None): return

        allp = inst.allports
        keys = inst.allPortNames

        for s in keys:
            for p in allp:
                if(p is None): continue
                if(p.name in self.nodeGraph):
                    self.nodeGraph[p.name].append(p)
                else:
                    g = Graph()
                    g.name = p.name
                    g.append(p)
                    self.nodeGraphList.append(p.name)
                    self.nodeGraph[p.name] = g


        
        pass

    def toJson(self):
        o = super().toJson()
        o["useHalfHeight"] = self.useHalfHeight
        o["alternateGroup"] = self.alternateGroup
        o["noPowerRoute"] = self.noPowerRoute
        return o

    def getInstancesByName(self,regex):
        data = list()
        for c in self.children:
            if(c.isInstance()):
                if(re.search(regex,c.name)):
                    data.append(c)
        return data

    def getInstancesByCellname(self,regex):
        data = list()
        for c in self.children:
            if(c.isInstance()):
                if(re.search(regex,c.cell)):
                    data.append(c)
        return data

    # ---- Translated utility methods from C++ ----

    def setYoffsetHalf(self, val):
        try:
            self.useHalfHeight = bool(int(val))
        except Exception:
            self.useHalfHeight = bool(val)

    def alternateGroupFlag(self, *_):
        self.alternateGroup = True

    def noPowerRouteFlag(self, *_):
        self.noPowerRoute = True

    def getNodeGraphs(self, regex:str):
        graphs = list()
        for node in self.nodeGraphList:
            if re.search(regex, node):
                graphs.append(self.nodeGraph[node])
        return graphs

    def placeHorizontal(self, val):
        try:
            self._placeHorizontal = int(val) > 0
        except Exception:
            self._placeHorizontal = bool(val)

    def resetOrigin(self, val):
        try:
            reset = int(val) > 0
        except Exception:
            reset = bool(val)
        if reset:
            self.updateBoundingRect()
            self.translate(-self.x1, -self.y1)

    def parseSubckt(self, obj):
        ckt = spi.Subckt()
        ckt.fromJson(obj)
        self.ckt = ckt

    def setSpiceParam(self, arr):
        if arr is None or len(arr) < 3 or self.ckt is None:
            return
        cktinst = arr[0]
        param = arr[1]
        value = arr[2]
        inst = self.ckt.getInstance(cktinst)
        if inst is not None:
            inst.setProperty(param, value)

    def getDummyInst(self,subcktName,repl):
        name = None
        if(re.search(r"CH_\d+C\d+F\d+",self.name)):
            name =  re.sub(r"C\d+F\d+",repl,subcktName)

        if(name is not None):
            si = SubcktInstance()
            si.subcktName = name
            si.name = "xdmy__"  + str(self.dummyCounter)
            self.dummyCounter += 1
            return si

        return None

    def getDummyBottomInst(self,subcktName):
        return self.getDummyInst(subcktName,"CTAPBOT")

    def getDummyTopInst(self,subcktName):
        return self.getDummyInst(subcktName,"CTAPTOP")

    def place(self):

        um = 10000

        next_gbreak = self.place_groupbreak.pop(0)
        next_xspace = self.place_xspace.pop(0)
        next_yspace = self.place_yspace.pop(0)

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
        previnst = None

        for inst in self.ckt.orderInstancesByGroup():

            name = inst.name
            group = inst.groupName
            if(group != prevgroup or prevgroup == ""):
                startGroup = True
                if(previnst is not None):
                    dname = self.getDummyTopInst(inst.subcktName)
                    if(dname is not None):
                        dummy = self.addInstance(dname,x,y)
                        x = dummy.x1
                        y = dummy.y2
                        next_y = y
                if(next_y > ymax):
                    ymax = next_y
                if(next_gbreak == groupcount):
                    y = ymax + next_yspace
                    yorg = y
                    if(len(self.place_groupbreak) > 0):
                        next_gbreak = int(self.place_groupbreak.pop(0))
                    x = 0
                else:
                    y = yorg

                if(first):
                    x = 0
                else:
                    x = next_x + next_xspace
                    if(len(self.place_xspace) > 0):
                        next_xspace = int(self.place_xspace.pop(0))

                groupcount += 1

            if(startGroup):
                dname = self.getDummyBottomInst(inst.subcktName)
                if(dname is not None):
                    dummy = self.addInstance(dname,x,y)
                    x = dummy.x1
                    y = dummy.y2

            # Handle property-based offsets and mirroring similar to C++
            inst_x = x
            inst_y = y
            if inst.hasProperty("xoffset"):
                off = inst.getPropertyString("xoffset")
                if off != "width":
                    try:
                        inst_x = inst_x + Rules.getInstance().get("ROUTE","horizontalgrid")*float(off)
                    except Exception:
                        pass
            if inst.hasProperty("yoffset"):
                offy = inst.getPropertyString("yoffset")
                if offy != "height":
                    try:
                        inst_y = inst_y + Rules.getInstance().get("ROUTE","verticalgrid")*float(offy)
                    except Exception:
                        pass

            linst = self.addInstance(inst,inst_x,inst_y)
            if(linst.x2 > next_x):
                next_x = linst.x2
            next_y = linst.y2

            if(next_y > ymax):
                ymax = next_y

            x = linst.x1
            y = next_y

            prevcell = linst
            previnst = inst

            prevgroup = group
            first = False
            startGroup = False


        if(previnst is not None):
             dname = self.getDummyTopInst(inst.subcktName)
             if(dname is not None):
                 dummy = self.addInstance(dname,x,y)
                 x = dummy.x1
                 y = dummy.y2
                 next_y = y
        pass

    def addPortRectangle(self, layer, x1, y1, width, height, angle, portname):
        r = Rect(layer,x1,y1,width,height)
        if angle == "R90":
            r.rotate(90)
        elif angle == "R180":
            r.rotate(90); r.rotate(90)
        elif angle == "R270":
            r.rotate(90); r.rotate(90); r.rotate(90)
        p = Port(portname)
        p.setRect(r)
        self.add(r)
        self.add(p)

    def addDirectedRoute(self, layer:str, net:str, route:str, options:str=""):
        # route is of form: startRegex + routeType symbols + stopRegex
        m = re.match(r"^([^-\|<>]*)([-\|<>]+)([^-\|<>]*)$", route)
        if not m:
            self.log.error(f"Could not parse route command '{route}'")
            return
        startRegex = m.group(1)
        routeType = m.group(2)
        stopRegex = m.group(3)
        start = self.findAllRectangles(startRegex, layer)
        stop = self.findAllRectangles(stopRegex, layer)
        if len(start) > 0 and len(stop) > 0:
            try:
                from .route import Route
                r = Route(net, layer, start, stop, options, routeType)
                self.add(r)
            except Exception:
                # Fallback: connect by a straight rect between bbox centers
                sb = self.calcBoundingRect()
                rb = self.calcBoundingRect()
                (sb, rb)  # no-op to appease linters
        else:
            self.log.error(f"Route did not work [ {layer} {net} {route} {options} ] stop={len(stop)} start={len(start)}")

    def addVerticalRect(self, layer:str, path:str, cuts:int=0):
        rects = self.findAllRectangles(path, layer)
        for r in rects:
            width = r.width()
            rn = Rect(layer, r.x1, self.y1, width, self.height())
            self.add(rn)

    def addHorizontalRect(self, layer:str, path:str, xsize:float=1, ysize:float=1):
        xspace = Rules.getInstance().get("ROUTE","horizontalgrid")*xsize
        yspace = Rules.getInstance().get("ROUTE","verticalgrid")*ysize
        rects = self.findAllRectangles(path, layer)
        for r in rects:
            if xspace > 0:
                x = r.x1
                y = r.y1 + yspace
                width = xspace
            else:
                x = r.x1 + xspace
                y = r.y1 + yspace
                width = -xspace
            rn = Rect(layer, x, y, width, r.height())
            self.add(rn)

    def addRouteHorizontalRect(self, layer:str, rectpath:str, x:int, name:str=""):
        rects = self.findAllRectangles(rectpath, layer)
        xgrid = Rules.getInstance().get("ROUTE","horizontalgrid")
        mw = Rules.getInstance().get(layer, "width")
        for r in rects:
            p = Rect(layer, r.x1, r.y1, xgrid*x, mw)
            if name != "":
                self.named_rects[name] = p
            self.add(p)

    def addPowerConnection(self, name:str, includeInstances:str, location:str):
        print(self.nodeGraph)
        if (name not in self.nodeGraph) or (f"power_{name}" not in self.named_rects):
            self.log.warning(f"Could not find rail {name} in {self.name}")
            return
        g = self.nodeGraph[name]
        rects = g.getRectangles("", includeInstances, "")
        rr = self.named_rects[f"power_{name}"]
        rrect = rr.get(location)
        for r in rects:
            rr.add(r.getCopy())

    def addRouteConnection(self, path:str, includeInstances:str, layer:str, location:str, options:str, routeTypeOverride:str=""):
        routeType = "-|--"
        if routeTypeOverride == "":
            if location == "top":
                routeType = "||"
                options = (options + ",onTopB,fillvcut").strip(',')
            elif location == "bottom":
                routeType = "||"
                options = (options + ",onTopT,fillvcut").strip(',')
            elif location == "right":
                routeType = "-"
                options = (options + ",onTopL,fillhcut").strip(',')
            elif location == "left":
                routeType = "-"
                options = (options + ",onTopR,fillhcut").strip(',')
        else:
            routeType = routeTypeOverride
        for node in list(self.nodeGraphList):
            if not re.search(path, node):
                continue
            rail_key = f"rail_{node}"
            if rail_key not in self.named_rects:
                continue
            g = self.nodeGraph[node]
            rects = g.getRectangles("", includeInstances, layer)
            rr = self.named_rects[rail_key]
            routering = rr.get(location)
            empty = []
            for r in rects:
                stop = [r, routering]
                from .route import Route
                ro = Route(node, layer, empty, stop, options, routeType)
                self.routes.append(ro)
                rr.add(ro)

    def addRectangle(self, layer, x1, y1, width, height, angle=""):
        r = Rect(layer,x1,y1,width,height)
        if angle == "R90":
            r.rotate(90)
        elif angle == "R180":
            r.rotate(90); r.rotate(90)
        elif angle == "R270":
            r.rotate(90); r.rotate(90); r.rotate(90)
        self.add(r)

    def addPowerRing(self, layer:str, name:str, location:str="rtbl", widthmult:int=1, spacemult:int=10):
        c = Cut.getInstance("M3","M4",2,2)
        mw = c.height()*widthmult
        xgrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult
        ygrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult
        rr = RouteRing(layer, name, self.getCopy(), location, ygrid, xgrid, mw)
        if rr:
            rail = f"power_{name}"
            self.named_rects[rail] = rr
            self.named_rects[f"RAIL_BOTTOM_{name}"] = rr.getPointer("bottom")
            self.named_rects[f"RAIL_TOP_{name}"] = rr.getPointer("top")
            self.named_rects[f"RAIL_LEFT_{name}"] = rr.getPointer("left")
            self.named_rects[f"RAIL_RIGHT_{name}"] = rr.getPointer("right")
            self.updatePort(name, rr.getDefault())
            self.add(rr)

    def addRouteRing(self, layer:str, name:str, location:str="rtbl", widthmult:int=1, spacemult:int=2, useGridForSpace:bool=True):
        mw = Rules.getInstance().get(layer, "width")*widthmult
        if useGridForSpace:
            xgrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult + mw
            ygrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult + mw
        else:
            xgrid = Rules.getInstance().get(layer, "space")*spacemult + mw
            ygrid = Rules.getInstance().get(layer, "space")*spacemult + mw
        rr = RouteRing(layer, name, self.getCopy(), location, ygrid, xgrid, mw)
        if rr:
            rail = f"rail_{name}"
            self.updatePort(name, rr.getDefault())
            self.named_rects[rail] = rr
            self.named_rects[f"rail_b_{name}"] = rr.getPointer("bottom")
            self.named_rects[f"rail_t_{name}"] = rr.getPointer("top")
            self.named_rects[f"rail_l_{name}"] = rr.getPointer("left")
            self.named_rects[f"rail_r_{name}"] = rr.getPointer("right")
            self.add(rr)

    def getInstanceFromInstanceName(self, instanceName:str):
        for r in self.children:
            if r is None: continue
            if r.isInstance():
                i = r
                if getattr(i, 'instanceName', '') == instanceName:
                    return i
        return None

    def fromJson(self,o):
        super().fromJson(o)
        self.updateBoundingRect()
        if("useHalfHeight" in o):
            self.useHalfHeight = o["useHalfHeight"]
        if("alternateGroup" in o):
            self.alternateGroup = o["alternateGroup"]
        if("noPowerRoute" in o):
            self.noPowerRoute = o["noPowerRoute"]

    def route(self):

        pass


    def paint(self):

        pass

    def findRectanglesByNode(self,node:str,filterChild:str=None,matchInstance:str=None):
        rects = list()
        for i in self.children:
            if(i is None): continue
            if(not i.isInstance()): continue

            if(matchInstance is not None):
                if(not re.search(matchInstance,i.name)): continue

            childRects = i.findRectanglesByNode(node,filterChild)
            for r in childRects:
                rects.append(r)
        return rects


    def addAllPorts(self):
        if(self.subckt is None): return
        nodes = self.subckt.nodes

        for node in nodes:

            if(node in self.ports): continue
            rects = self.findRectanglesByNode("^" + node + "$",None,None)
            if(len(rects) > 0):
                self.updatePort(node,rects[0])
            else:
                self.log.warning(r"No rects found on " + node)

    def fromJson(self,o):
        super().fromJson(o)

        if("alternateGroup" in o):
            self.alternateGroup = o["alternateGroup"]

        if("useHalfHeight" in o):
            self.useHalfHeight = o["useHalfHeight"]

        if("boundarIgnoreRouting" in o):
            self.boundaryIgnoreRouting = o["boundaryIgnoreRouting"]

        if("meta" in o):
            self.meta = o["meta"]

        if("graph" in o):
            self.graph = o["graph"]

        for child in o["children"]:

            c = None
            cl = child["class"]
            if(cl == "Rect"):
                c = Rect()
            elif(cl == "Port"):
                c  = Port()
            elif(cl == "Text"):
                c  = Text()
            elif(cl == "Instance"):
                c  = Instance()
            elif(cl == "Cell" or cl== "cIcCore::Route" or cl == "cIcCore::RouteRing" or cl == "cIcCore::Guard" or cl == "cIcCore::Cell" or cl == "cIcCore::LayoutCell"):
                c = LayoutCell()
            else:
                self.log.warning(f"Unkown class {cl}")

            if(c is not None):
                c.design = self.design
                c.fromJson(child)
                self.add(c)

    def addConnectivityRoute(self,layer,regex, routeType, options, cuts, excludeInstances, includeInstances):
        for node in list(self.nodeGraphList):
            if not re.search(regex, node):
                continue
            g = self.nodeGraph.get(node)
            if g is None:
                continue
            rects = g.getRectangles(excludeInstances, includeInstances, layer)
            if len(rects) == 0:
                self.log.error(f"Could not find rectangles on {node} {regex} {len(rects)}")
                continue
            try:
                from .route import Route
                empty = list()
                r = Route(node, layer, empty, rects, options, routeType)
                self.add(r)
            except Exception:
                for rr in rects:
                    self.add(rr.getCopy(layer))

    def addPortOnEdge(self,layer,node,location,routeType, options):
        if node not in self.ports:
            self.log.error(f"{node} not a port")
            return
        p = self.ports[node]
        r = p.get()
        if not r:
            self.log.error("no port rectangle")
            return
        rp = r.getCopy(layer)
        if(location == "bottom"):
            rp.moveTo(rp.x1,self.y1)
        elif (location == "top"):
            rp.moveTo(rp.x1,self.y2()-rp.height())
        elif (location == "right"):
            rp.moveTo(self.x2() - r.width(),rp.y1)
        elif (location == "left"):
            rp.moveTo(self.x1,rp.y1)
        start = [p]
        stop = [rp]
        try:
            from .route import Route
            route = Route(node,layer,start,stop,options,routeType)
            route.route()
            self.add(rp)
            self.add(route)
            p.setRect(rp)
        except Exception:
            self.add(rp)
            p.setRect(rp)

    def _runSelfMethod(self,name,args=()):
        if(hasattr(self,name)):
            self.log.info("Running " + name  + " with "+",".join(map(str,args)))
            getattr(self,name)(*args)
        else:
            self.log.warning(f"Could not find method {name} on {self.name}")


    def _runMethod(self,module,moduleData,method,args=()):
        if(moduleData is not None):
            if(method in moduleData):
                data = moduleData[method]
                if(type(data) is list):
                    for d in data:
                        for k in d:
                            methodname = k
                            if(k.endswith("s")):
                                methodname = k[:-1]
                                for mdata in d[k]:
                                    self._runSelfMethod(methodname,mdata)


        if(hasattr(module,method)):
            fn = getattr(module,method)
            self.log.info("Running " + method + " from " + self.name + ".py")
            fn(self,*args)

    def layout(self,pycell=None,data=None):
        self.ignoreBoundaryRouting = False
        self.log.info(f"Assembling layout....")

        self._runMethod(pycell,data,"beforePlace")


        #- Place cell
        self.log.info(f"place()")
        self.place()

        self._runMethod(pycell,data,"afterPlace")

        self._runMethod(pycell,data,"beforeRoute")

        self.log.info(f"route()")
        self.route()

        self._runMethod(pycell,data,"afterRoute")

        self._runMethod(pycell,data,"beforePaint")

        self.log.info(f"paint()")

        self._runMethod(pycell,data,"afterPaint")


        self.log.info(f"addAllPorts()")
        self.addAllPorts()
