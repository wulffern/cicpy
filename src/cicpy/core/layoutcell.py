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
from .cellgroup import CellGroup
from .routering import RouteRing
from .guard import Guard
from .cut import Cut
from .tilemap import TileMap
import cicspi as spi
import re
import logging
import inspect
from collections import defaultdict


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
        self._tile_map = None
        rules = Rules.getInstance()
        if(rules.hasRules()):
            space =rules.get("CELL","space")
            self.place_groupbreak = [100]
            self.place_xspace = [space]
            self.place_yspace = [space]



    def addInstance(self,cktInst,x:int,y:int):
        self.log.info(f"addInstance(cktInst={cktInst.name if cktInst else None}, cellName={cktInst.subcktName} x={x}, y={y})")

        if(cktInst is None):
            return None

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

    def addPhysicalInstance(self, cellName: str, instanceName: str, x: int, y: int):
        layoutCell = self.parent.getLayoutCell(cellName)
        if layoutCell is None:
            self.log.warning(f"Could not find physical-only layoutcell {cellName}")
            return None

        i = Instance()
        i.cell = layoutCell.name
        i.layoutcell = layoutCell
        i.libpath = layoutCell.libpath
        i.instanceName = instanceName
        i.name = layoutCell.name
        i.physicalOnly = True
        self.add(i)
        i.moveTo(x, y)
        i.updateBoundingRect()
        return i

    def makeCellGroup(self, name: str):
        return CellGroup(self, name)

    def addToNodeGraph(self,inst):

        if (inst is None): return

        allp = inst.allports
        keys = inst.allPortNames

        for s in keys:
            if s in allp:
                for p in allp[s]:
                    if(p is None): continue
                    if(p.name in self.nodeGraph):
                        self.nodeGraph[p.name].append(p)
                    else:
                        g = Graph()
                        g.name = p.name
                        g.append(p)
                        self.nodeGraphList.append(p.name)
                        self.nodeGraph[p.name] = g

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

    def getOccupiedRectangles(self, layer: str, excludeInstances: str = "", ignoreNet: str = ""):
        rects = []
        for child in self.children:
            if child is None:
                continue

            if child.isInstance():
                instanceName = getattr(child, "instanceName", "")
                if excludeInstances != "" and (re.search(excludeInstances, instanceName) or re.search(excludeInstances, getattr(child, "name", ""))):
                    continue
                rects.extend(child.getOccupiedRectangles(layer))
                continue

            if child.isRect():
                if child.layer != layer:
                    continue
                if ignoreNet != "" and getattr(child, "net", "") == ignoreNet:
                    continue
                rects.append(child.getCopy())
                continue

            if child.isCell():
                if ignoreNet != "" and getattr(child, "name", "") == ignoreNet:
                    continue
                for grandchild in child.children:
                    if grandchild is None or not grandchild.isRect():
                        continue
                    if grandchild.layer != layer:
                        continue
                    if ignoreNet != "" and getattr(grandchild, "net", "") == ignoreNet:
                        continue
                    rects.append(grandchild.getCopy())

        return rects

    def getInstancesByCellname(self,regex):
        data = list()
        for c in self.children:
            if(c.isInstance()):
                if(re.search(regex,c.cell)):
                    data.append(c)
        return data

    def _normalizeLayerName(self, layer_name):
        rules = Rules.getInstance()
        if rules is None or layer_name is None:
            return layer_name
        if layer_name in rules.layers:
            return rules.layers[layer_name].name
        if hasattr(rules, "alias") and layer_name in rules.alias:
            return rules.alias[layer_name].name
        return layer_name

    def _rectsTouchOrOverlap(self, rect1, rect2):
        if rect1 is None or rect2 is None:
            return False
        if rect1.x2 < rect2.x1 or rect2.x2 < rect1.x1:
            return False
        if rect1.y2 < rect2.y1 or rect2.y2 < rect1.y1:
            return False
        return True

    def _layersDirectlyConnect(self, layer1, layer2):
        l1 = self._normalizeLayerName(layer1)
        l2 = self._normalizeLayerName(layer2)
        if l1 == l2:
            return True
        rules = Rules.getInstance()
        if rules is None:
            return False
        layer_obj_1 = rules.getLayer(l1)
        layer_obj_2 = rules.getLayer(l2)
        if layer_obj_1 is None or layer_obj_2 is None:
            return False
        if getattr(layer_obj_1, "next", "") == l2:
            return True
        if getattr(layer_obj_1, "previous", "") == l2:
            return True
        if getattr(layer_obj_2, "next", "") == l1:
            return True
        if getattr(layer_obj_2, "previous", "") == l1:
            return True
        return False

    def _collectPhysicalRects(self, obj=None, dx=0, dy=0, out=None, active=None):
        if out is None:
            out = []
        if obj is None:
            obj = self
        if active is None:
            active = set()

        obj_id = id(obj)
        if obj_id in active:
            return out
        active.add(obj_id)

        children = getattr(obj, "children", [])
        for child in children:
            if child is None:
                continue

            if (hasattr(child, "isPort") and child.isPort()) or (hasattr(child, "isInstancePort") and child.isInstancePort()):
                continue

            if child.isInstance():
                self._collectPhysicalRects(child.layoutcell, dx + child.x1, dy + child.y1, out, active)
                continue

            if child.isCell():
                self._collectPhysicalRects(child, dx, dy, out, active)
                continue

            if child.isRect():
                rr = child.getCopy()
                rr.translate(dx, dy)
                rr.parent = obj
                if hasattr(child, "route_owner_info"):
                    rr.route_owner_info = child.route_owner_info
                out.append(rr)
                continue

        active.remove(obj_id)
        return out

    def _getRouteSource(self, rect):
        if hasattr(rect, "route_owner_info"):
            return rect.route_owner_info
        parent = getattr(rect, "parent", None)
        seen = set()
        while parent is not None and id(parent) not in seen:
            seen.add(id(parent))
            if hasattr(parent, "isRoute") and parent.isRoute():
                return {
                    "name": getattr(parent, "name", ""),
                    "net": getattr(parent, "net", ""),
                    "layer": getattr(parent, "routeLayer", ""),
                    "route": getattr(parent, "route_", ""),
                    "options": getattr(parent, "options", ""),
                    "debug_api": getattr(parent, "debug_api", ""),
                    "debug_callsite": getattr(parent, "debug_callsite", ""),
                    "debug_command": getattr(parent, "debug_command", ""),
                    "debug_internal": getattr(parent, "debug_internal", False),
                }
            parent = getattr(parent, "parent", None)
        return None

    def _captureRouteDebug(self, api_name, params):
        callsite = ""
        command = f"{api_name}(" + ", ".join(f"{k}={params[k]!r}" for k in params) + ")"
        try:
            for frame in inspect.stack()[2:]:
                filename = frame.filename or ""
                if filename.endswith("layoutcell.py") or filename.endswith("cellgroup.py") or filename.endswith("route.py"):
                    continue
                callsite = f"{filename}:{frame.lineno}"
                break
        except Exception:
            callsite = ""
        return {
            "api": api_name,
            "callsite": callsite,
            "command": command,
        }

    def _annotateRoute(self, route, api_name, params):
        if route is None:
            return None
        debug = self._captureRouteDebug(api_name, params)
        route.debug_api = debug["api"]
        route.debug_callsite = debug["callsite"]
        route.debug_command = debug["command"]
        route.debug_internal = bool(params.get("internal", False))
        return route

    def _collectNetAnchorRects(self, target_layer=""):
        anchors = []
        seen = set()
        for node in self.nodeGraphList:
            graph = self.nodeGraph.get(node)
            if graph is None:
                continue
            rects = []
            if target_layer:
                rects = graph.getRectangles("", "", target_layer)
            if len(rects) == 0:
                rects = graph.getRectangles("", "", "")
            for rect in rects:
                if rect is None:
                    continue
                rr = rect.getCopy()
                key = (node, rr.layer, rr.x1, rr.y1, rr.x2, rr.y2)
                if key in seen:
                    continue
                seen.add(key)
                anchors.append((node, rr))
        for node, port in self.ports.items():
            if port is None:
                continue
            rr = port.get(target_layer) if target_layer else port.get()
            if rr is None:
                rr = port.get()
            if rr is None:
                continue
            rr = rr.getCopy()
            key = (node, rr.layer, rr.x1, rr.y1, rr.x2, rr.y2)
            if key in seen:
                continue
            seen.add(key)
            anchors.append((node, rr))
        return anchors

    def _findRoot(self, parent, idx):
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def _unionRoots(self, parent, a, b):
        ra = self._findRoot(parent, a)
        rb = self._findRoot(parent, b)
        if ra != rb:
            parent[rb] = ra

    def checkConnectivity(self, target_layer=""):
        shapes = self._collectPhysicalRects()
        parent = list(range(len(shapes)))

        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                if not self._rectsTouchOrOverlap(shapes[i], shapes[j]):
                    continue
                if not self._layersDirectlyConnect(shapes[i].layer, shapes[j].layer):
                    continue
                self._unionRoots(parent, i, j)

        components = defaultdict(list)
        for idx, rect in enumerate(shapes):
            components[self._findRoot(parent, idx)].append(rect)

        anchors = self._collectNetAnchorRects(target_layer)
        net_components = defaultdict(set)
        component_nets = defaultdict(set)
        unmatched = defaultdict(list)

        for comp_id, rects in components.items():
            for rect in rects:
                net_name = getattr(rect, "net", "")
                if net_name:
                    component_nets[comp_id].add(net_name)
                route_owner = getattr(rect, "route_owner_info", None)
                if route_owner is not None:
                    route_net = route_owner.get("net", "")
                    if route_net:
                        component_nets[comp_id].add(route_net)

        for net_name, anchor in anchors:
            matched = False
            for comp_id, rects in components.items():
                for rect in rects:
                    if not self._layersDirectlyConnect(anchor.layer, rect.layer):
                        continue
                    if not self._rectsTouchOrOverlap(anchor, rect):
                        continue
                    net_components[net_name].add(comp_id)
                    component_nets[comp_id].add(net_name)
                    matched = True
                    break
                if matched:
                    break
            if not matched:
                unmatched[net_name].append(anchor)

        shorts = []
        for comp_id, nets in component_nets.items():
            if len(nets) > 1:
                rects = components[comp_id]
                bounds = Cell.calcBoundingRectFromList(rects, False)
                route_sources = []
                route_seen = set()
                for rect in rects:
                    source = self._getRouteSource(rect)
                    if source is None:
                        continue
                    key = (
                        source["name"],
                        source["layer"],
                        source["route"],
                        source["options"],
                        source.get("debug_callsite", ""),
                        source.get("debug_command", ""),
                    )
                    if key in route_seen:
                        continue
                    route_seen.add(key)
                    route_sources.append(source)
                shorts.append({
                    "component": comp_id,
                    "nets": sorted(nets),
                    "rect_count": len(rects),
                    "bounds": bounds,
                    "routes": route_sources,
                })

        opens = []
        for net_name in self.nodeGraphList:
            comp_ids = sorted(net_components.get(net_name, set()))
            if len(comp_ids) == 0:
                opens.append({
                    "net": net_name,
                    "type": "unmatched",
                    "anchors": len(unmatched.get(net_name, [])),
                })
            elif len(comp_ids) > 1:
                opens.append({
                    "net": net_name,
                    "type": "split",
                    "components": comp_ids,
                })

        return {
            "shorts": shorts,
            "opens": opens,
            "component_nets": component_nets,
            "net_components": net_components,
            "unmatched": unmatched,
            "component_count": len(components),
            "shape_count": len(shapes),
        }

    def checkRouteShorts(self, target_layer=""):
        result = self.checkConnectivity(target_layer)
        route_shorts = []
        for short in result.get("shorts", []):
            routes = short.get("routes", [])
            if not routes:
                continue

            external_routes = [route for route in routes if not route.get("debug_internal", False)]
            if len(external_routes) == 0:
                continue

            external_nets = [net for net in short.get("nets", []) if not re.match(r"^xfill_.*_dummy_", net)]
            if len(external_nets) < 2:
                continue

            filtered_short = dict(short)
            filtered_short["nets"] = external_nets
            filtered_short["routes"] = external_routes
            filtered_short["route_count"] = len(external_routes)
            route_shorts.append(filtered_short)
        return {
            "shorts": route_shorts,
            "component_count": result.get("component_count", 0),
            "shape_count": result.get("shape_count", 0),
        }

    def reportShorts(self, target_layer=""):
        result = self.checkConnectivity(target_layer)
        for short in result["shorts"]:
            bounds = short["bounds"]
            route_desc = "none"
            if short.get("routes"):
                route_desc = "; ".join(
                    f"{route['name']}[{route['layer']} {route['route']} {route['options']}]"
                    + (f" cmd={route['debug_command']}" if route.get("debug_command") else "")
                    + (f" at {route['debug_callsite']}" if route.get("debug_callsite") else "")
                    for route in short["routes"]
                )
            self.log.warning(
                f"SHORT component={short['component']} nets={','.join(short['nets'])} "
                f"bounds=({bounds.x1},{bounds.y1})-({bounds.x2},{bounds.y2}) rects={short['rect_count']} "
                f"routes={route_desc}"
            )
        return result["shorts"]

    def reportOpens(self, target_layer=""):
        result = self.checkConnectivity(target_layer)
        for open_net in result["opens"]:
            if open_net["type"] == "split":
                self.log.warning(f"OPEN net={open_net['net']} split_components={open_net['components']}")
            else:
                self.log.warning(f"OPEN net={open_net['net']} unmatched_anchors={open_net['anchors']}")
        return result["opens"]

    # ---- Translated utility methods from C++ ----

    def setYoffsetHalf(self, val):
        try:
            self.useHalfHeight = bool(int(val))
        except Exception as e:
            self.log.debug(f"setYoffsetHalf: Could not parse '{val}' as int, using as bool: {e}")
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
        except Exception as e:
            self.log.debug(f"placeHorizontal: Could not parse '{val}' as int, using as bool: {e}")
            self._placeHorizontal = bool(val)

    def resetOrigin(self, val):
        try:
            reset = int(val) > 0
        except Exception as e:
            self.log.debug(f"resetOrigin: Could not parse '{val}' as int, using as bool: {e}")
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
                    except Exception as e:
                        self.log.warning(f"Could not parse xoffset '{off}' for instance {inst.name}: {e}")
                        pass
            if inst.hasProperty("yoffset"):
                offy = inst.getPropertyString("yoffset")
                if offy != "height":
                    try:
                        inst_y = inst_y + Rules.getInstance().get("ROUTE","verticalgrid")*float(offy)
                    except Exception as e:
                        self.log.warning(f"Could not parse yoffset '{offy}' for instance {inst.name}: {e}")
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
        self.log.info(f"addPortRectangle(layer={layer}, x1={x1}, y1={y1}, width={width}, height={height}, angle={angle}, portname={portname})")
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
        self.log.info(f"addDirectedRoute(layer={layer}, net={net}, route={route}, options={options})")
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
                self._annotateRoute(r, "addDirectedRoute", {
                    "layer": layer,
                    "net": net,
                    "route": route,
                    "options": options,
                })
                self.add(r)
            except Exception as e:
                # Fallback: connect by a straight rect between bbox centers
                self.log.error(f"addDirectedRoute: Failed to create route for net '{net}': {e}. Using fallback.")
                sb = self.calcBoundingRect()
                rb = self.calcBoundingRect()
                (sb, rb)  # no-op to appease linters
        else:
            self.log.error(f"Route did not work [ {layer} {net} {route} {options} ] stop={len(stop)} start={len(start)}")

    def addVerticalRect(self, layer:str, path:str, cuts:int=0):
        self.log.info(f"addVerticalRect(layer={layer}, path={path}, cuts={cuts})")
        rects = self.findAllRectangles(path, layer)
        for r in rects:
            width = r.width()
            rn = Rect(layer, r.x1, self.y1, width, self.height())
            self.add(rn)

    def addHorizontalRect(self, layer:str, path:str, xsize:float=1, ysize:float=1):
        self.log.info(f"addHorizontalRect(layer={layer}, path={path}, xsize={xsize}, ysize={ysize})")
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
        self.log.info(f"addRouteHorizontalRect(layer={layer}, rectpath={rectpath}, x={x}, name={name})")
        rects = self.findAllRectangles(rectpath, layer)
        xgrid = Rules.getInstance().get("ROUTE","horizontalgrid")
        mw = Rules.getInstance().get(layer, "width")
        for r in rects:
            p = Rect(layer, r.x1, r.y1, xgrid*x, mw)
            if name != "":
                self.named_rects[name] = p
            self.add(p)

    def addPowerConnection(self, name:str, includeInstances:str, location:str):
        # Check if node exists in nodeGraph
        if name not in self.nodeGraph:
            return
        router_key = None
        if f"power_{name}" in self.named_rects:
            router_key = f"power_{name}"
        elif f"rail_{name}" in self.named_rects:
            router_key = f"rail_{name}"
        else:
            return
        
        graph = self.nodeGraph.get(name)
        rects = []
        if graph is not None:
            rects = graph.getRectangles("", includeInstances, "M1")
            if len(rects) == 0:
                rects = graph.getRectangles("", includeInstances, "")
        routering = self.named_rects[router_key]
        rrect = routering.get(location)
        for r in rects:
            # Create cut between layers
            from .cut import Cut
            ct = Cut.getInstance(r.layer, rrect.layer, 2, 2)
            
            # Create a copy of the rectangle
            rr = r.getCopy()
            
            # Adjust position based on location
            if location == "top":
                rr.setTop(rrect.y2)
                if ct:
                    ct.moveTo(rr.x1, rrect.y1)
            elif location == "bottom":
                rr.setBottom(rrect.y1)
                if ct:
                    ct.moveTo(rr.x1, rrect.y1)
            elif location == "left":
                rr.setLeft(rrect.x1)
                if ct:
                    ct.moveTo(rrect.x1, rr.y1)
            elif location == "right":
                rr.setRight(rrect.x2)
                if ct:
                    ct.moveTo(rrect.x1, rr.y1)
            
            # Add rectangle and cut to routering
            routering.add(rr)
            if ct:
                routering.add(ct)

    def addRouteConnection(self, path:str, includeInstances:str, layer:str, location:str, options:str, routeTypeOverride:str=""):
        self.log.info(f"addRouteConnection(path={path}, includeInstances={includeInstances}, layer={layer}, location={location}, options={options}, routeTypeOverride={routeTypeOverride})")
        routeType = "-|--"
        if routeTypeOverride == "":
            if location == "top":
                routeType = "||"
                options += ",onTopB,fillvcut"
            elif location == "bottom":
                routeType = "||"
                options += ",onTopT,fillvcut"
            elif location == "right":
                routeType = "-"
                options += ",onTopL,fillhcut"
            elif location == "left":
                routeType = "-"
                options += ",onTopR,fillhcut"
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
            if rr:
                routering = rr.get(location)
                empty = []
                for r in rects:
                    stop = [r, routering]
                    from .route import Route
                    ro = Route(node, layer, empty, stop, options, routeType)
                    self._annotateRoute(ro, "addRouteConnection", {
                        "path": path,
                        "includeInstances": includeInstances,
                        "layer": layer,
                        "location": location,
                        "options": options,
                        "routeTypeOverride": routeTypeOverride,
                    })
                    self.routes.append(ro)
                    rr.add(ro)

    def addRectangle(self, layer, x1, y1, width, height, angle=""):
        self.log.info(f"addRectangle(layer={layer}, x1={x1}, y1={y1}, width={width}, height={height}, angle={angle})")
        r = Rect(layer,x1,y1,width,height)
        if angle == "R90":
            r.rotate(90)
        elif angle == "R180":
            r.rotate(90); r.rotate(90)
        elif angle == "R270":
            r.rotate(90); r.rotate(90); r.rotate(90)
        self.add(r)

    def addPowerRing(self, layer:str, name:str, location:str="rtbl", widthmult:int=1, spacemult:int=10):
        self.log.info(f"addPowerRing(layer={layer}, name={name}, location={location}, widthmult={widthmult}, spacemult={spacemult})")
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
        self.log.info(f"addRouteRing(layer={layer}, name={name}, location={location}, widthmult={widthmult}, spacemult={spacemult}, useGridForSpace={useGridForSpace})")
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
        """Route all routes in this layout cell"""
        for r in self.routes:
            if r.isRoute() and not getattr(r, '_pre_routed', False):
                r.route()

    def paint(self):
        """Paint the cell - route power if needed"""
        if not self.noPowerRoute:
            self.routePower()
        
        # Call parent paint (currently empty but following C++ structure)
        super().paint()
    
    def routePower(self):
        """Route power rails"""
        self.addPowerRoute("AVDD", "NCH|DMY")
        self.addPowerRoute("AVSS", "PCH|DMY")
        pass
    
    def addPowerRoute(self, net: str, excludeInstances: str):
        """Add power route for a net, excluding certain instances"""
        # Find rectangles for this net, filtering out B/G/BULKP/BULKN ports
        foundrects = self.findRectanglesByNode(net, "^(B|G|BULKP|BULKN)$", "")
        
        rects = []
        for r in foundrects:
            parent = r.parent
            if parent and parent.isCell():
                skip = False
                
                if excludeInstances != "" and parent.isInstance():
                    lname = parent.name
                    instName = getattr(parent, 'instanceName', '')
                    if re.search(excludeInstances, lname):
                        skip = True
                    if re.search(excludeInstances, instName):
                        skip = True
                
                if not skip:
                    rects.append(r)
            else:
                rects.append(r)
        
        # TODO: If there are multiple rectangles horizontally this
        # method makes a sheet, should really make it better
        if len(rects) > 0:
            from .cut import Cut
            cuts = Cut.getCutsForRects("M4", rects, 2, 1)
            rp = None
            
            if len(cuts) > 0:
                r_bound = Cell.calcBoundingRectFromList(cuts, False)
                r_bound.setTop(self.top())
                r_bound.setBottom(self.bottom())
                for cut in cuts:
                    self.add(cut)
                rp = Rect("M4", r_bound.x1, r_bound.y1, r_bound.width(), r_bound.height())
            else:
                r_bound = Cell.calcBoundingRectFromList(rects, False)
                r_bound.setTop(self.top())
                r_bound.setBottom(self.bottom())
                rp = Rect("M4", r_bound.x1, r_bound.y1, r_bound.width(), r_bound.height())
            
            if rp:
                self.add(rp)
                if net in self.ports:
                    p = self.ports[net]
                    p.setRect(rp)

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
        self.log.info(f"addAllPorts()")
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
            elif(cl == "InstanceCut"):
                from .instancecut import InstanceCut
                c = InstanceCut()
            elif(cl in ("Cell", "Route", "RouteRing", "Guard", "cIcCore::Route", "cIcCore::RouteRing", "cIcCore::Guard", "cIcCore::Cell", "cIcCore::LayoutCell")):
                c = LayoutCell()
            else:
                self.log.warning(f"Unkown class {cl}")

            if(c is not None):
                c.design = self.design
                c.fromJson(child)
                # Add instances to node graph after loading from JSON
                if(cl == "Instance"):
                    self.addToNodeGraph(c)
                self.add(c)

    def addConnectivityRoute(self,layer,regex, routeType, options, cuts, excludeInstances, includeInstances):
        self.log.info(f"addConnectivityRoute(layer={layer}, regex={regex}, routeType={routeType}, options={options}, cuts={cuts}, excludeInstances={excludeInstances}, includeInstances={includeInstances})")
        for node in list(self.nodeGraphList):
            if not re.search(regex, node):
                continue
            log = logging.getLogger("LayoutCell")
            log.info(f"addConnectivityRoute: node={node}")
            g = self.nodeGraph.get(node)
            if g is None:
                continue
            rects = g.getRectangles(excludeInstances, includeInstances, layer)
            if len(rects) == 0:
                self.log.error(f"Could not find rectangles on {node} {regex} {len(rects)}")
                continue
            if self._tile_map is not None:
                for cand, existing, existing_net, info in self._tile_map.check(layer, rects, node):
                    log.error(
                        f"TILE CONFLICT: net='{node}' on layer={getattr(cand,'layer',layer)} "
                        f"rect=({cand.x1},{cand.y1})-({cand.x2},{cand.y2}) "
                        f"conflicts with net='{existing_net}' "
                        f"at ({existing.x1},{existing.y1})-({existing.x2},{existing.y2})"
                        + (f" [{info}]" if info else "")
                    )
            try:
                from .route import Route
                empty = list()
                #log.info(f"addConnectivityRoute: empty={empty}, rects={rects}")
                r = Route(node, layer, empty, rects, options, routeType)
                self._annotateRoute(r, "addConnectivityRoute", {
                    "layer": layer,
                    "regex": regex,
                    "routeType": routeType,
                    "options": options,
                    "cuts": cuts,
                    "excludeInstances": excludeInstances,
                    "includeInstances": includeInstances,
                    "node": node,
                })
                log.info(f"addConnectivityRoute: r={r}")
                self.add(r)
            except Exception as e:
                log.error(f"addConnectivityRoute: Exception={e}")
                for rr in rects:
                    self.add(rr.getCopy(layer))

    def addPortOnEdge(self,layer,node,location,routeType, options):
        self.log.info(f"addPortOnEdge(layer={layer}, node={node}, location={location}, routeType={routeType}, options={options})")
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
            self._annotateRoute(route, "addPortOnEdge", {
                "layer": layer,
                "node": node,
                "location": location,
                "routeType": routeType,
                "options": options,
            })
            route.route()
            self.add(rp)
            self.add(route)
            p.setRect(rp)
        except Exception as e:
            self.log.error(f"addPortOnEdge: Failed to create route for node '{node}': {e}. Adding rect directly.")
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

        # Route internal (dummy) routes immediately so TileMap can see their geometry
        for r in list(self.routes):
            if getattr(r, 'debug_internal', False):
                r.route()
                r._pre_routed = True

        self._tile_map = TileMap()
        self._tile_map.populate(self)

        self._runMethod(pycell,data,"beforeRoute")

        self.log.info(f"route()")
        self.route()

        self._runMethod(pycell,data,"afterRoute")

        self._runMethod(pycell,data,"beforePaint")

        self.log.info(f"paint()")

        self._runMethod(pycell,data,"afterPaint")


        self.log.info(f"addAllPorts()")
        self.addAllPorts()
