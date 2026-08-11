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
from .routegroup import RouteGroup
from .guard import Guard
from .cut import Cut
import cicspi as spi
import math
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
        self.cellgroups = []
        self.guiHierarchy = []
        self.log = logging.getLogger("LayoutCell")
        self.dummyCounter = 0
        self.routeKeepouts = defaultdict(list)
        rules = Rules.getInstance()
        if(rules is not None and rules.hasRules()):
            space =rules.get("CELL","space")
            self.place_groupbreak = [100]
            self.place_xspace = [space]
            self.place_yspace = [space]



    #- Terminal order of a four terminal device in the netlist: D G S B.
    DEVICE_TERMINALS = ("D", "G", "S", "B")

    def _diodeVariant(self, cktInst):
        """The diode-connected twin of this device's cell, if it applies.

        A library can carry a variant that ties drain to gate inside the
        cell, named by suffixing ``D``. In a library built for it that
        tie is a single pattern column the cell already had spare: no
        via, no routing layer, nothing outside the abutment box. When
        the netlist shorts a device's gate to its own drain and such a
        cell exists, it is strictly better than anything drawn at
        assembly time, so take it.

        Returns None when the device is not diode connected, when no
        such cell exists, or when the netlist does not give four
        terminals in the expected order — this is a substitution, and a
        substitution that is not certain should not happen.
        """
        #- A design may decline the substitution. It buys a free tie --
        #- one character of M1, no via, nothing to route -- at the cost
        #- of a layout cell that is not the schematic cell, and that
        #- difference is only invisible while LVS is run at the top. Put
        #- the same cell on both sides, as a per-stack flow does, and it
        #- has to be compared against itself: layout 2 devices / 3 nets
        #- against schematic 1 / 4, because the tie is in the M1 pattern
        #- and not in the netlist.
        #-
        #- Off, the gate-to-drain connection becomes a route like any
        #- other -- and a short, local, stack-internal one.
        if not getattr(self, "useDiodeVariant", True):
            return None
        name = getattr(cktInst, "subcktName", "")
        if not name or name.endswith("D"):
            return None
        nodes = getattr(cktInst, "nodes", None) or getattr(cktInst, "pins", None)
        if not nodes or len(nodes) != len(self.DEVICE_TERMINALS):
            return None
        if nodes[0] != nodes[1]:
            return None
        candidate = name + "D"
        if self.parent.getLayoutCell(candidate) is None:
            return None
        self.log.info(
            f"{cktInst.name}: {nodes[0]} on both D and G, using {candidate}")
        return candidate

    def addInstance(self,cktInst,x:int,y:int):
        self.log.info(f"addInstance(cktInst={cktInst.name if cktInst else None}, cellName={cktInst.subcktName} x={x}, y={y})")

        if(cktInst is None):
            return None

        i = Instance()
        subcktName = self._diodeVariant(cktInst) or cktInst.subcktName
        layoutCell = self.parent.getLayoutCell(subcktName)
        if layoutCell is None and hasattr(self.parent, "generatePrimitiveLayout"):
            layoutCell = self.parent.generatePrimitiveLayout(cktInst.subcktName, cktInst)
        if layoutCell is None:
            raise ValueError(f"Could not find layout cell for {cktInst.subcktName}")
        i.cell = layoutCell.name
        #- The name the SCHEMATIC uses, which is not always the layout
        #- cell: a diode connected device is placed as the D variant,
        #- and the netlist knows nothing of that substitution. Anything
        #- generating a netlist from placed instances has to use this,
        #- or it writes a layout-only cell into a schematic -- which is
        #- what puts a layout-only diode variant into a generated stack
        #- netlist and makes it fail LVS against a schematic that has no
        #- such cell.
        i.schematicCell = getattr(cktInst, "subcktName", "") or layoutCell.name
        i.layoutcell = layoutCell
        i.libpath = layoutCell.libpath
        #- the .mag on disk still starts at the cell's load origin;
        #- the model was normalised to (0,0) at load, and the painted
        #- reference needs the negated origin to land the disk
        #- geometry on the model (magicdesign.MagicFile.loadLayoutCell)
        sx, sy = getattr(layoutCell, "libshift", (0, 0))
        i.xcell = -int(sx)
        i.ycell = -int(sy)
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
        from .cellgroup import CellGroup
        group = CellGroup(self, name)
        self.cellgroups.append(group)
        self.add(group)
        return group

    def detachPlacementChild(self, target, keepParent=None):
        """Remove ``target`` from the placement tree before re-parenting it."""
        if target is None:
            return False

        def remove_from(parent):
            removed = False
            children = getattr(parent, "children", [])
            if parent is not keepParent and target in children:
                children.remove(target)
                removed = True
            routes = getattr(parent, "routes", [])
            if parent is not keepParent and target in routes:
                routes.remove(target)
            if removed:
                try:
                    parent.updateBoundingRect()
                except Exception:
                    pass
                return True
            for child in list(children):
                if child is None or child is target:
                    continue
                if child.isInstance() or child.isCut():
                    continue
                if hasattr(child, "children") and remove_from(child):
                    return True
            return False

        return remove_from(self)

    def iterJsonChildren(self):
        """Yield flat physical children for legacy .cic JSON readers."""
        seen = set()
        group_classes = {"CellGroup", "StackGroup", "RouteBundle"}

        def visit(children):
            for child in children:
                if child is None:
                    continue
                class_name = child.__class__.__name__
                if class_name in group_classes:
                    yield from visit(getattr(child, "children", []))
                    continue
                oid = id(child)
                if oid in seen:
                    continue
                seen.add(oid)
                yield child

        yield from visit(getattr(self, "children", []))

    def iterPlacementChildren(self):
        """Yield placement tree children once, including logical cellgroups.

        Cellgroups are currently stored as a side table while the same member
        instances also remain in ``children``. The de-duplicating traversal lets
        callers become hierarchy-aware before ownership is moved fully under
        the groups.
        """
        seen = set()
        stack = list(getattr(self, "children", []))
        for group in getattr(self, "cellgroups", []):
            if group is not None:
                stack.append(group)

        while stack:
            child = stack.pop(0)
            if child is None:
                continue
            oid = id(child)
            if oid in seen:
                continue
            seen.add(oid)
            yield child

            if child.isInstance() or child.isCut():
                continue
            if hasattr(child, "children"):
                stack[0:0] = list(child.children)

    def iterInstances(self, regex="", by="instanceName", includeCuts=False):
        for child in self.iterPlacementChildren():
            if child is None:
                continue
            if not (child.isInstance() or (includeCuts and child.isCut())):
                continue
            if regex:
                value = getattr(child, by, "")
                if not re.search(regex, value):
                    continue
            yield child

    def _searchChildren(self):
        """Flatten cellgroup-owned instances into the search space so
        path-style ``findAllRectangles`` lookups (e.g. ``"xn_diode1:D"``)
        resolve under single-ownership where instances live in
        ``stack.children`` rather than directly in ``layout.children``.
        """
        return list(self.iterPlacementChildren())

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

    def _access_rect_key(self, rect):
        return (rect.layer, rect.x1, rect.y1, rect.x2, rect.y2)

    def _instance_matches_route_scope(self, inst, includeInstances="", excludeInstances=""):
        instance_name = getattr(inst, "instanceName", "")
        cell_name = getattr(inst, "name", "")
        if excludeInstances and (re.search(excludeInstances, instance_name) or re.search(excludeInstances, cell_name)):
            return False
        if includeInstances and not (re.search(includeInstances, instance_name) or re.search(includeInstances, cell_name)):
            return False
        return True

    def _directNodeAccessRects(self, net, layer, includeInstances="", excludeInstances="", skipInstances=None, anymetal=False):
        graph = self.nodeGraph.get(net)
        if graph is None:
            return []
        skip = set(skipInstances or [])
        rects = []
        seen = set()
        for port in getattr(graph, "ports", []):
            inst = getattr(port, "parent", None)
            if inst is None or not inst.isInstance():
                continue
            instance_name = getattr(inst, "instanceName", "")
            if instance_name in skip:
                continue
            if not self._instance_matches_route_scope(inst, includeInstances=includeInstances, excludeInstances=excludeInstances):
                continue

            rr = None
            if hasattr(port, "get"):
                rr = port.get(layer) if layer else port.get()

            if rr is None:
                continue
            key = self._access_rect_key(rr)
            if key in seen:
                continue
            seen.add(key)
            rects.append(rr)
        return rects

    def _groupNodeAccessRects(self, net, layer, includeGroups="", options=""):
        rects = []
        suppressed = set()
        seen = set()
        for group in getattr(self, "cellgroups", []):
            if group is None:
                continue
            if includeGroups and not re.search(includeGroups, getattr(group, "name", "")):
                continue
            # Only suppress member pins when the group owns internal routing
            # for the net (route_bundles / direct / diode / dummy). With no
            # internal routing the boundary port is just one rep pin; keeping
            # the other member pins lets the parent route tie them all.
            group_routes = set()
            for stack in getattr(group, "stacks", []):
                if hasattr(stack, "routedNets"):
                    group_routes.update(stack.routedNets())
            if hasattr(group, "routedNets"):
                group_routes.update(group.routedNets())
            if hasattr(group, "_boundary_nets") and net in group._boundary_nets() and net in group_routes:
                suppressed.update(group.memberNames())
            for port in group.exportBoundaryPorts(layer=layer, options=options):
                if getattr(port, "name", "") != net:
                    continue
                rr = port.get(layer)
                if rr is None:
                    continue
                key = self._access_rect_key(rr)
                if key in seen:
                    continue
                seen.add(key)
                rects.append(rr)
        return rects, suppressed

    def getNodeAccessRects(self, net, layer, includeInstances="", excludeInstances="", includeGroups="", anymetal=False, options=""):
        rects = []
        suppressed = set()
        if not includeInstances:
            group_rects, suppressed = self._groupNodeAccessRects(net, layer, includeGroups=includeGroups, options=options)
            rects.extend(group_rects)
        rects.extend(
            self._directNodeAccessRects(
                net,
                layer,
                includeInstances=includeInstances,
                excludeInstances=excludeInstances,
                skipInstances=suppressed,
                anymetal=anymetal,
            )
        )
        out = []
        seen = set()
        for rect in rects:
            key = self._access_rect_key(rect)
            if key in seen:
                continue
            seen.add(key)
            out.append(rect)
        return out

    def toJson(self):
        o = super().toJson()
        o["children"] = [child.toJson() for child in self.iterJsonChildren()]
        o["useHalfHeight"] = self.useHalfHeight
        o["alternateGroup"] = self.alternateGroup
        o["noPowerRoute"] = self.noPowerRoute
        if self.cellgroups:
            o["cellgroups"] = [g.toJson() for g in self.cellgroups if g is not None]
        elif self.guiHierarchy:
            o["cellgroups"] = self.guiHierarchy
        return o

    def getInstancesByName(self,regex):
        data = list()
        for c in self.iterInstances(regex, by="name"):
            data.append(c)
        return data

    def getSortedInstancesByInstanceName(self,regex):
        data = list()
        for c in self.iterInstances(regex, by="instanceName"):
            data.append(c)
        if(len(data) == 0):
            raise ValueError(f"Missing instance {regex}")

        data = sorted(data, key=lambda item: item.instanceName)

        return data

    def getSortedInstancesByGroupName(self, groupName, excludeInstances=""):
        data = list()
        for c in self.iterInstances():
            instance_name = getattr(c, "instanceName", "")
            if excludeInstances != "" and (
                re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(c, "name", ""))
            ):
                continue
            if self._instanceGroupName(c) == groupName:
                data.append(c)
        if(len(data) == 0):
            raise ValueError(f"Missing group {groupName}")

        data = sorted(data, key=lambda item: self._naturalInstanceNameKey(item.instanceName))

        return data

    def _instanceGroupName(self, inst):
        group = getattr(inst, "groupName", "")
        if group:
            return group
        name = getattr(inst, "instanceName", "")
        m = re.search(r"^(x\D+)", name, re.I)
        if m is not None:
            return m.groups(0)[0]
        return ""

    def _naturalInstanceNameKey(self, name):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]

    def getOccupiedRectangles(self, layer: str, excludeInstances: str = "", ignoreNet: str = "", includeBoundaries: bool = False):
        rects = []
        for child in self.iterPlacementChildren():
            if child is None:
                continue

            if child.isInstance():
                instanceName = getattr(child, "instanceName", "")
                if excludeInstances != "" and (re.search(excludeInstances, instanceName) or re.search(excludeInstances, getattr(child, "name", ""))):
                    continue
                if includeBoundaries:
                    rr = child.calcBoundingRect().getCopy(layer)
                    rr.parent = child
                    rects.append(rr)
                rects.extend(child.getOccupiedRectangles(layer))
                continue

            if child.isRect():
                if child.layer != layer:
                    continue
                if ignoreNet != "" and getattr(child, "net", "") == ignoreNet:
                    continue
                rects.append(child.getCopy())
                continue

        return rects

    def addRouteKeepoutRect(self, layer, rect, margin=0, name=""):
        self.log.info(
            f"addRouteKeepoutRect(layer={layer}, margin={margin}, name={name}, rect={None if rect is None else rect.layer})"
        )
        if rect is None:
            return None
        rr = rect.getCopy(layer) if layer else rect.getCopy()
        if margin:
            rr.adjust(-margin, -margin, margin, margin)
        rr.keepoutName = name or f"keepout_{layer}_{len(self.routeKeepouts[layer])}"
        rr.keepoutLayer = layer or rr.layer
        self.routeKeepouts[rr.keepoutLayer].append(rr)
        return rr

    def getRouteKeepouts(self, layer, keepoutFilter=""):
        rects = []
        for rr in self.routeKeepouts.get(layer, []):
            if keepoutFilter and not re.search(keepoutFilter, getattr(rr, "keepoutName", "")):
                continue
            rects.append(rr.getCopy())
        return rects

    def getInstancesByCellname(self,regex):
        data = list()
        for c in self.iterInstances(regex, by="cell"):
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
        #- a pure question about the TECHNOLOGY, asked once per pair of
        #- rects by the connectivity flood -- 3.5 million times on
        #- LELOTEMP_CMP, for the handful of distinct answers a .tech
        #- file has. Cached on the Rules instance, so a new technology
        #- gets a new cache and there is nothing to invalidate.
        rules = Rules.getInstance()
        if rules is not None:
            cache = getattr(rules, "_layer_connect_cache", None)
            if cache is None:
                cache = rules._layer_connect_cache = {}
            key = (layer1, layer2)
            hit = cache.get(key)
            if hit is None:
                hit = cache[key] = self._layersDirectlyConnectUncached(
                    layer1, layer2)
            return hit
        return self._layersDirectlyConnectUncached(layer1, layer2)

    def _layersDirectlyConnectUncached(self, layer1, layer2):
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
        mat1 = getattr(layer_obj_1, "material", None)
        mat2 = getattr(layer_obj_2, "material", None)
        try:
            from .layer import Material
            cut_mat = Material.CUT
        except Exception:
            cut_mat = None
        # Cut aliases sharing GDS number+datatype are the same physical via
        # (e.g. ``CO`` / ``NDIFFC`` / ``PDIFFC`` / ``PCO`` all GDS 33). Only
        # apply this to cuts — diffusion aliases (``OD`` / ``PDIFF`` /
        # ``NDIFF`` / ``PTAP`` / ``NTAP``) also share GDS 22 but are isolated
        # by transistor gates, so unifying them cascades nets into shorts.
        if cut_mat is not None and mat1 == cut_mat and mat2 == cut_mat:
            n1 = getattr(layer_obj_1, "number", None)
            n2 = getattr(layer_obj_2, "number", None)
            d1 = getattr(layer_obj_1, "datatype", None)
            d2 = getattr(layer_obj_2, "datatype", None)
            if n1 is not None and n1 == n2 and d1 == d2:
                return True
        # Stack-adjacency by name (each layer points at its immediate next /
        # previous cut or metal). Bidirectional check.
        if getattr(layer_obj_1, "next", "") == l2:
            return True
        if getattr(layer_obj_1, "previous", "") == l2:
            return True
        if getattr(layer_obj_2, "next", "") == l1:
            return True
        if getattr(layer_obj_2, "previous", "") == l1:
            return True
        # Stack-adjacency by GDS *for cut endpoints only*: a layer's
        # ``next`` / ``previous`` can name any cut alias; if the target cut
        # shares its GDS pair with the other layer, treat as connected.
        # This covers cases like ``PO`` whose ``next=CO`` should connect to
        # ``NDIFFC``-named contacts that share GDS 33 with ``CO``.
        def _gds(obj):
            return (getattr(obj, "number", None), getattr(obj, "datatype", None))
        gds1, gds2 = _gds(layer_obj_1), _gds(layer_obj_2)
        for direction in ("next", "previous"):
            tgt_name = getattr(layer_obj_1, direction, "")
            tgt = rules.getLayer(tgt_name) if tgt_name else None
            if (tgt is not None
                    and getattr(tgt, "material", None) == cut_mat
                    and _gds(tgt) == gds2 and mat2 == cut_mat):
                return True
            tgt_name = getattr(layer_obj_2, direction, "")
            tgt = rules.getLayer(tgt_name) if tgt_name else None
            if (tgt is not None
                    and getattr(tgt, "material", None) == cut_mat
                    and _gds(tgt) == gds1 and mat1 == cut_mat):
                return True
        return False

    def _isConnectivityPropagationLayer(self, layer_name):
        """Connectivity checks only propagate through explicit conductors."""
        rules = Rules.getInstance()
        if rules is None:
            return False
        layer_obj = rules.getLayer(self._normalizeLayerName(layer_name))
        if layer_obj is None:
            return False
        try:
            from .layer import Material
            allowed = {Material.METAL, Material.POLY, Material.CUT}
        except Exception:
            return False
        return getattr(layer_obj, "material", None) in allowed

    def _layersConnectForConnectivity(self, layer1, layer2):
        if not self._isConnectivityPropagationLayer(layer1):
            return False
        if not self._isConnectivityPropagationLayer(layer2):
            return False
        return self._layersDirectlyConnect(layer1, layer2)

    def _connectedComponentsFromRects(self, rects):
        components = []
        seen = [False] * len(rects)
        for i, rect in enumerate(rects):
            if seen[i]:
                continue
            queue = [i]
            seen[i] = True
            comp = []
            while queue:
                idx = queue.pop()
                current = rects[idx]
                comp.append(current)
                for j, other in enumerate(rects):
                    if seen[j]:
                        continue
                    if not self._layersDirectlyConnect(current.layer, other.layer):
                        continue
                    if not self._rectsTouchOrOverlap(current, other):
                        continue
                    seen[j] = True
                    queue.append(j)
            components.append(comp)
        return components

    def collapseRepresentativeRects(self, net, rects):
        if not rects:
            return []
        same_net_rects = [rr for rr in self._collectPhysicalRects() if getattr(rr, "net", "") == net]
        if not same_net_rects:
            return list(rects)
        components = self._connectedComponentsFromRects(same_net_rects)
        grouped = {}
        floating_index = 0
        for rect in rects:
            key = None
            for idx, comp in enumerate(components):
                if any(self._layersDirectlyConnect(rect.layer, rr.layer) and self._rectsTouchOrOverlap(rect, rr) for rr in comp):
                    key = ("component", idx)
                    break
            if key is None:
                key = ("floating", floating_index)
                floating_index += 1
            grouped.setdefault(key, []).append(rect)
        out = []
        for comp_rects in grouped.values():
            out.append(sorted(comp_rects, key=lambda r: (r.x2, r.centerY(), r.y1), reverse=True)[0])
        out.sort(key=lambda r: (r.centerY(), r.centerX(), r.x1))
        return out

    def _collectPhysicalRects(self, obj=None, dx=0, dy=0, out=None, active=None,
                              include_ports=False):
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
                #- Ports are skipped by default: they are not conductors
                #- in their own right and counting them would double the
                #- geometry of every net.
                #-
                #- A router needs them anyway, and needs them marked as
                #- PINS rather than as wire. A pin of another net is not
                #- merely occupied space to be shared -- it is space that
                #- must not be crossed at all. Every routing failure
                #- measured so far has been a trunk run through another
                #- net's pin, and none were visible here because of
                #- this `continue`.
                if include_ports:
                    pr = child.getCopy()
                    pr.translate(dx, dy)
                    pr.parent = obj
                    pr.isPin = True
                    #- getCopy() returns a plain Rect and drops the
                    #- port's identity, so the net has to be carried
                    #- across by hand -- without it every pin reads as
                    #- net "?" and none can be told from another.
                    if not pr.net:
                        pr.setNet(getattr(child, "name", "") or "")
                    out.append(pr)
                continue

            if child.isInstance():
                child_cell = getattr(child, "layoutcell", None)
                if child_cell is None:
                    child_cell = getattr(child, "_cell_obj", None)
                # Lazy resolve from the design — instances loaded from JSON
                # may reference cells that hadn't been loaded yet at
                # ``fromJson`` time. Without this fallback the connectivity
                # check misses every metal/via inside the instance body and
                # nets fragment into separate components.
                if child_cell is None:
                    cell_name = getattr(child, "cell", "")
                    design = getattr(self, "design", None)
                    if cell_name and design is not None:
                        resolved = design.cells.get(cell_name)
                        if resolved is not None:
                            child.layoutcell = resolved
                            child._cell_obj = resolved
                            child_cell = resolved
                if child_cell is not None:
                    start = len(out)
                    self._collectPhysicalRects(child_cell, dx + child.x1, dy + child.y1, out, active, include_ports)
                    self._attributeInstanceBody(child, out, start, dx, dy)
                continue

            if child.isCell():
                self._collectPhysicalRects(child, dx, dy, out, active, include_ports)
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

    def _attributeInstanceBody(self, inst, out, start, dx=0, dy=0):
        """Resolve the rects inside one instance: a net, or an obstacle.

        An instance KNOWS what its terminals are wired to -- its
        InstancePorts carry the net and the placed pin rect -- and until
        now that knowledge never reached the geometry: every rect inside
        a device body came out with no net, was reported as "?", and had
        to be TOLERATED on the pin layer so that a via could land on a
        pin at all. That tolerance is the hole every remaining boundary
        routing failure fell through -- a via pad on a device's own
        rail, relabelled by the connectivity flood, reported as two
        signal nets shorting.

        The rule is the obvious one:

          - a body rect overlapping one of the instance's own pins, on
            the pin's layer, belongs to that pin's NET
          - everything else inside the instance belongs to NO net and is
            a HARD OBSTACLE -- marked ``device_metal``, blocked by the
            track map for every net, never tolerated

        The net FLOODS through the body: a rect touching an attributed
        rect of the same layer takes its net, to a fixpoint. Without
        this, only the rect directly under a pin was attributed, and the
        pin's own conductor one row up -- present in every device --
        blocked the pin's own via: measured, every boundary net in every
        subcell came back "no path, closest approach 0 away", the search
        unable to take its first step off its own pin. Same-layer
        adjacency only: a chain that crosses layers inside a device is
        rare, and a missed one leaves an obstacle, never a wrong net.

        What stays unattributed after the flood is a HARD OBSTACLE. It
        belongs to no terminal reachable from outside, so no via may
        land on it and no run may cross it, for any net.
        """
        #- an instance that IS part of a net -- a via cut placed by a
        #- route -- attributes its whole body to that net: it has no
        #- ports for the flood to seed from, and marking a route's own
        #- via enclosures as obstacles blocks the route from itself
        owner = getattr(inst, "net", "") or ""
        if not owner:
            p = getattr(inst, "parent", None)
            seen_p = set()
            while p is not None and id(p) not in seen_p:
                seen_p.add(id(p))
                if hasattr(p, "isRoute") and p.isRoute():
                    owner = getattr(p, "net", "") or ""
                    break
                p = getattr(p, "parent", None)
        if owner:
            for rr in out[start:]:
                if not getattr(rr, "net", "") and not getattr(rr, "isPin", False):
                    rr.setNet(owner)
            return

        pins = []
        for pi in getattr(inst, "children", []) or []:
            if pi is None:
                continue
            if not ((hasattr(pi, "isPort") and pi.isPort())
                    or (hasattr(pi, "isInstancePort") and pi.isInstancePort())):
                continue
            net = getattr(pi, "name", "") or ""
            if not net:
                continue
            layer = getattr(pi, "routeLayer", "") or getattr(pi, "layer", "")
            pins.append((net, layer,
                         pi.x1 + dx, pi.y1 + dy, pi.x2 + dx, pi.y2 + dy))
        body = [rr for rr in out[start:]
                if not getattr(rr, "net", "") and not getattr(rr, "isPin", False)]
        #- seed: the rect directly under a pin carries the pin's net
        for rr in body:
            layer = getattr(rr, "layer", "")
            for pnet, pl, px1, py1, px2, py2 in pins:
                if pl != layer:
                    continue
                if (rr.x1 < px2 and rr.x2 > px1
                        and rr.y1 < py2 and rr.y2 > py1):
                    rr.setNet(pnet)
                    break
        #- flood: touching metal of the same layer is the same conductor.
        #- Touch includes abutment (closed intervals) -- cicpy draws a
        #- conductor as abutting rects more often than overlapping ones.
        #-
        #- Only the ATTRIBUTED rects of the rect's own layer can extend
        #- the flood, so those are what it scans. It used to rescan the
        #- whole body for every unattributed rect on every pass, which
        #- is the same answer for O(n^3) work: 2.0 BILLION getattr calls
        #- and 109 of 213 profiled seconds on LELOTEMP_CMP, a cell with
        #- four stacks. The index is kept in BODY ORDER, and a rect
        #- joins it the moment it is attributed, so the neighbour that
        #- wins a tie is the same one as before, pass for pass.
        seed_order = {id(rr): i for i, rr in enumerate(body)}
        attributed = {}
        for i, rr in enumerate(body):
            if getattr(rr, "net", ""):
                attributed.setdefault(rr.layer, []).append((i, rr))
        pending = [rr for rr in body if not getattr(rr, "net", "")]
        changed = True
        while changed and pending:
            changed = False
            rest = []
            for rr in pending:
                hit = None
                for _, other in attributed.get(rr.layer, ()):
                    if (rr.x1 <= other.x2 and rr.x2 >= other.x1
                            and rr.y1 <= other.y2 and rr.y2 >= other.y1):
                        hit = other
                        break
                if hit is None:
                    rest.append(rr)
                    continue
                rr.setNet(hit.net)
                changed = True
                same = attributed.setdefault(rr.layer, [])
                same.append((seed_order[id(rr)], rr))
                same.sort(key=lambda t: t[0])
            pending = rest
        for rr in body:
            if not getattr(rr, "net", ""):
                rr.device_metal = True

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

    @staticmethod
    def _getShapeOwner(rect):
        """Name the instance or cut a rect came out of.

        A bridge whose two rects have no `route` is geometry somebody
        PLACED, and without this the report says so only by omission --
        which reads as "unknown" and sends the reader looking at the
        router. Naming the instance turns four anonymous boxes into
        "these two devices touch".
        """
        parent = getattr(rect, "parent", None)
        seen = set()
        chain = []
        while parent is not None and id(parent) not in seen:
            seen.add(id(parent))
            if hasattr(parent, "isRoute") and parent.isRoute():
                return None
            iname = getattr(parent, "instanceName", "")
            cname = getattr(parent, "name", "")
            if iname and iname != cname:
                chain.append(f"{iname}:{cname}" if cname else iname)
            elif cname:
                chain.append(str(cname))
            parent = getattr(parent, "parent", None)
        if not chain:
            return None
        #- innermost first, and drop the top cell: it is on every line
        return " < ".join(chain[:3])

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
            if self._ignoreConnectivityNet(node):
                continue
            graph = self.nodeGraph.get(node)
            if graph is None:
                continue
            rects = []
            if target_layer:
                rects = graph.getRectangles("^xfill_", "", target_layer)
            if len(rects) == 0:
                rects = graph.getRectangles("^xfill_", "", "")
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
            if self._ignoreConnectivityNet(node):
                continue
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

    def _ignoreConnectivityNet(self, net_name):
        return bool(net_name) and str(net_name).startswith("xfill_")

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

    def _shortBridges(self, indices, adjacency, shapes, limit=8):
        """Where two nets actually touch, rectangle by rectangle.

        A shorted component says *that* two nets are joined. This says
        *where*. Every rectangle that carries a net of its own is a seed;
        a breadth first sweep from all seeds at once labels the rest with
        whichever net reaches it first, so a wire with no net attribution
        of its own — a via pad, a piece of a guard — belongs to whatever
        it hangs off. Any adjacency whose two ends carry different labels
        is then a place the short is made, and cutting all of them would
        separate the nets.

        The labels of unattributed metal are a guess, so the *rectangles*
        reported are exact and the *net named on each side* is the nearest
        attribution rather than a proof. That is still the difference
        between a coordinate to look at and six hundred rectangles.
        """
        from collections import deque

        label = {}
        queue = deque()
        for idx in indices:
            net = getattr(shapes[idx], "net", "")
            if net and not self._ignoreConnectivityNet(net):
                label[idx] = net
                queue.append(idx)
        if not queue:
            return []

        while queue:
            i = queue.popleft()
            for j in adjacency.get(i, ()):
                if j in label:
                    continue
                label[j] = label[i]
                queue.append(j)

        bridges = []
        seen = set()
        for i in indices:
            li = label.get(i)
            if li is None:
                continue
            for j in adjacency.get(i, ()):
                lj = label.get(j)
                if lj is None or lj == li or j < i:
                    continue
                a, b = shapes[i], shapes[j]
                key = (li, lj, a.layer, b.layer,
                       int(a.x1), int(a.y1), int(b.x1), int(b.y1))
                if key in seen:
                    continue
                seen.add(key)
                bridges.append({
                    "nets": sorted((li, lj)),
                    "a": {
                        "layer": a.layer,
                        "rect": [int(a.x1), int(a.y1), int(a.x2), int(a.y2)],
                        "route": self._getRouteSource(a),
                        "owner": self._getShapeOwner(a),
                    },
                    "b": {
                        "layer": b.layer,
                        "rect": [int(b.x1), int(b.y1), int(b.x2), int(b.y2)],
                        "route": self._getRouteSource(b),
                        "owner": self._getShapeOwner(b),
                    },
                })
        #- the same pair of nets can meet in many places; show a few of
        #- each rather than eight instances of one
        bridges.sort(key=lambda x: (x["nets"], x["a"]["rect"]))
        out, per_pair = [], defaultdict(int)
        for bridge in bridges:
            pair = tuple(bridge["nets"])
            if per_pair[pair] >= 2:
                continue
            per_pair[pair] += 1
            out.append(bridge)
            if len(out) >= limit:
                break
        return out

    def checkConnectivity(self, target_layer=""):
        shapes = [
            rect for rect in self._collectPhysicalRects()
            if self._isConnectivityPropagationLayer(getattr(rect, "layer", ""))
        ]
        parent = list(range(len(shapes)))
        #- keep the edges, not just the union. A short report that says
        #- which nets ended up in one component tells you nothing about
        #- where they meet, and a component of six hundred rectangles is
        #- not something you find the bridge in by eye
        adjacency = defaultdict(list)

        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                if not self._rectsTouchOrOverlap(shapes[i], shapes[j]):
                    continue
                if not self._layersConnectForConnectivity(shapes[i].layer, shapes[j].layer):
                    continue
                adjacency[i].append(j)
                adjacency[j].append(i)
                self._unionRoots(parent, i, j)

        components = defaultdict(list)
        component_indices = defaultdict(list)
        for idx, rect in enumerate(shapes):
            root = self._findRoot(parent, idx)
            components[root].append(rect)
            component_indices[root].append(idx)

        anchors = self._collectNetAnchorRects(target_layer)
        net_components = defaultdict(set)
        component_nets = defaultdict(set)
        unmatched = defaultdict(list)

        for comp_id, rects in components.items():
            for rect in rects:
                net_name = getattr(rect, "net", "")
                if net_name and not self._ignoreConnectivityNet(net_name):
                    component_nets[comp_id].add(net_name)

        for net_name, anchor in anchors:
            matched = False
            if not self._isConnectivityPropagationLayer(anchor.layer):
                unmatched[net_name].append(anchor)
                continue
            for comp_id, rects in components.items():
                for rect in rects:
                    if not self._layersConnectForConnectivity(anchor.layer, rect.layer):
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
                    source_name = source.get("name", "") or source.get("net", "")
                    if source.get("debug_internal", False) or self._ignoreConnectivityNet(source_name):
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
                    "bridges": self._shortBridges(
                        component_indices[comp_id], adjacency, shapes),
                })

        opens = []
        for net_name in self.nodeGraphList:
            if self._ignoreConnectivityNet(net_name):
                continue
            comp_ids = sorted(
                comp_id for comp_id, nets in component_nets.items() if net_name in nets
            )
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

        components_bbox = {
            cid: Cell.calcBoundingRectFromList(rs, False)
            for cid, rs in components.items()
        }

        # Per-net anchor rects (instance-port locations). Used by the GUI to
        # draw flight lines between actual transistor ports instead of
        # component bbox centres.
        net_anchor_rects = defaultdict(list)
        for net_name, rect in anchors:
            net_anchor_rects[net_name].append(rect)

        return {
            "shorts": shorts,
            "opens": opens,
            "component_nets": component_nets,
            "net_components": net_components,
            "unmatched": unmatched,
            "components_bbox": components_bbox,
            "net_anchor_rects": net_anchor_rects,
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
            for bridge in short.get("bridges", ()):
                self.log.warning("  " + self.describeBridge(bridge))
        return result["shorts"]

    @staticmethod
    def describeBridge(bridge):
        """One line naming the two rectangles a short is made across."""
        def side(s):
            text = (f"{s['layer']} ({s['rect'][0]},{s['rect'][1]})-"
                    f"({s['rect'][2]},{s['rect'][3]})")
            route = s.get("route")
            if route:
                where = route.get("debug_callsite", "")
                text += f" [{route.get('name','')} {route.get('options','')}"
                text += f" at {where}]" if where else "]"
            elif s.get("owner"):
                text += f" [{s['owner']}]"
            return text
        return (f"BRIDGE {'|'.join(bridge['nets'])}: "
                f"{side(bridge['a'])} touches {side(bridge['b'])}")

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
            si = spi.SubcktInstance()
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

        #- The running placement point. The C++ place() starts it at the
        #- origin; without this the first dummy instance of a group reads
        #- x and y before the loop has assigned them
        x = 0
        y = 0

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
            #- fill devices belong to the LAYOUT generator
            #- (fillDummyTransistors); a schematic carries them only
            #- so LVS can match the physical cell. Placing them from
            #- the netlist would double every fill.
            if name.startswith("xfill_"):
                self.log.info(f"place: skipping schematic fill {name}")
                continue
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
        p.set(r)
        self.add(r)
        self.add(p)

    def addPortFromRect(self, node, rect, routeLayer=None, pinLayer=None):
        self.log.info(
            f"addPortFromRect(node={node}, routeLayer={routeLayer}, pinLayer={pinLayer}, rect={None if rect is None else rect.layer})"
        )
        if rect is None:
            self.log.error(f"addPortFromRect: no rectangle for node {node}")
            return None
        rr = rect.getCopy(routeLayer) if routeLayer else rect.getCopy()
        port = self.updatePort(node, rr, routeLayer=routeLayer, pinLayer=pinLayer)
        return port

    def addRouteFromRects(self, net, layer, startRects, stopRects, routeType, options=""):
        self.log.info(
            f"addRouteFromRects(net={net}, layer={layer}, routeType={routeType}, options={options}, start={len(startRects or [])}, stop={len(stopRects or [])})"
        )
        if not startRects or not stopRects:
            self.log.error(f"addRouteFromRects: missing rectangles for net {net}")
            return None
        from .route import Route
        route = Route(net, layer, startRects, stopRects, options, routeType)
        self._annotateRoute(route, "addRouteFromRects", {
            "net": net,
            "layer": layer,
            "routeType": routeType,
            "options": options,
            "start_count": len(startRects or []),
            "stop_count": len(stopRects or []),
        })
        self.add(route)
        route.route()
        return route

    def collectPhysicalRects(self, net="", layer="", root=None):
        rects = self._collectPhysicalRects(root) if root is not None else self._collectPhysicalRects()
        out = []
        for rect in rects:
            if layer and rect.layer != layer:
                continue
            if net and getattr(rect, "net", "") != net:
                continue
            out.append(rect)
        return out

    def addRouteRingOnRect(self, layer:str, name:str, rect:Rect, location:str="rtbl", widthmult:int=1, spacemult:int=2, useGridForSpace:bool=True, exportPort:bool=False):
        self.log.info(
            f"addRouteRingOnRect(layer={layer}, name={name}, location={location}, widthmult={widthmult}, spacemult={spacemult}, useGridForSpace={useGridForSpace}, exportPort={exportPort})"
        )
        if rect is None:
            self.log.error(f"addRouteRingOnRect: no rectangle for {name}")
            return None
        mw = Rules.getInstance().get(layer, "width")*widthmult
        if useGridForSpace:
            xgrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult + mw
            ygrid = Rules.getInstance().get("ROUTE","horizontalgrid")*spacemult + mw
        else:
            xgrid = Rules.getInstance().get(layer, "space")*spacemult + mw
            ygrid = Rules.getInstance().get(layer, "space")*spacemult + mw
        rr = RouteRing(layer, name, rect.getCopy(), location, ygrid, xgrid, mw)
        if rr:
            self.named_rects[f"ring_{name}"] = rr
            self.named_rects[f"ring_b_{name}"] = rr.getPointer("bottom")
            self.named_rects[f"ring_t_{name}"] = rr.getPointer("top")
            self.named_rects[f"ring_l_{name}"] = rr.getPointer("left")
            self.named_rects[f"ring_r_{name}"] = rr.getPointer("right")
            self.add(rr)
            if exportPort:
                self.addPortFromRect(name, rr.getDefault())
        return rr

    def addDirectedRoute(self, layer:str, net:str, route:str, options:str=""):
        """Resolve a `startPath{routeType}stopPath` route string and add the
        resulting Route to this layout. Returns the Route on success,
        ``None`` on parse / lookup / construction failure.
        """
        self.log.info(f"addDirectedRoute(layer={layer}, net={net}, route={route}, options={options})")
        # route is of form: startRegex + routeType symbols + stopRegex.
        # A bus index is written xnd1<0>, and < and > are also route type
        # characters, so the endpoints have to be masked before the split
        # or every bussed instance fails to parse.
        masked = re.sub(r"<\d+(?::\d+)?>", lambda mm: "\x00" * len(mm.group(0)), route)
        m = re.match(r"^([^-\|<>]*)([-\|<>]+)([^-\|<>]*)$", masked)
        if not m:
            self.log.error(f"Could not parse route command '{route}'")
            return None
        startRegex = route[m.start(1):m.end(1)]
        routeType = route[m.start(2):m.end(2)]
        stopRegex = route[m.start(3):m.end(3)]
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
                return r
            except Exception as e:
                self.log.error(f"addDirectedRoute: Failed to create route for net '{net}': {e}.")
                return None
        else:
            self.log.error(f"Route did not work [ {layer} {net} {route} {options} ] stop={len(stop)} start={len(start)}")
            return None

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

    def addPowerConnection(self, name:str, includeInstances:str, location:str, excludeInstances:str=""):
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
            rects = self.getNodeAccessRects(name, self._pinLayer(), includeInstances=includeInstances, excludeInstances=excludeInstances)
            if len(rects) == 0:
                rects = graph.getRectangles(excludeInstances, includeInstances, "")
        routering = self.named_rects[router_key]
        rrect = routering.get(location)
        for r in rects:
            # Create cut between layers
            from .cut import Cut
            ct = Cut.getInstance(r.layer, rrect.layer, 2, 2)
            if ct and ct.width() > r.width():
                ct1x2 = Cut.getInstance(r.layer, rrect.layer, 1, 2)
                ct2x1 = Cut.getInstance(r.layer, rrect.layer, 2, 1)
                if ct1x2 and ct1x2.width() <= r.width():
                    ct = ct1x2
                elif ct2x1 and ct2x1.width() <= r.width():
                    ct = ct2x1
                else:
                    ct = ct1x2 if (ct1x2 and (not ct2x1 or ct1x2.width() <= ct2x1.width())) else ct2x1
            
            # Create a copy of the rectangle
            rr = r.getCopy()
            
            # Adjust position based on location
            if location == "top":
                rr.setTop(rrect.y2)
                if ct:
                    ct.moveTo(rr.centerX() - ct.width()//2, rrect.y1)
            elif location == "bottom":
                rr.setBottom(rrect.y1)
                if ct:
                    ct.moveTo(rr.centerX() - ct.width()//2, rrect.y1)
            elif location == "left":
                rr.setLeft(rrect.x1)
                if ct:
                    ct.moveTo(rrect.x1, rr.centerY() - ct.height()//2)
            elif location == "right":
                rr.setRight(rrect.x2)
                if ct:
                    ct.moveTo(rrect.x1, rr.centerY() - ct.height()//2)
            
            # Add rectangle and cut to routering
            routering.add(rr)
            if ct:
                routering.add(ct)

    def addPowerStrap(self, name:str, includeInstances:str, location:str, excludeInstances:str="", widthmult:int=1, includeGroups:str="", align:str="center", terminals=None):
        """Connect a power net to its ring with a narrow strap on the ring's
        own layer, cut down to the pin.

        This is the counterpart to :meth:`addPowerConnection` for libraries
        whose cells put their pins on the lowest layer and leave the metal
        above empty. ``addPowerConnection`` copies the pin rectangle and
        stretches it to the ring on the *pin's* layer, with the via at the
        ring: from the source of an upper device that drags the pin's layer
        down across the drain and gate of everything below it. It is what
        shorted a gate ladder in one design and it shorts a whole row of
        any library shaped that way. Its geometry cannot be changed --
        designs in the wild depend on it -- so the correct behaviour
        lives here instead.

        Three things are different, and all three are needed:

        * the strap is on the ring's layer, not the pin's,
        * the via sits on the pin, not up at the ring,
        * the strap is one routing width, not the full width of the pin. A
          pin can be wider than the device pitch and overlap its neighbours
          in x, so a pin-wide strap blocks the column that a signal needs
          for its own via stack even when it shorts nothing.
        """
        self.log.info(
            f"addPowerStrap(name={name}, includeInstances={includeInstances}, location={location}, excludeInstances={excludeInstances}, widthmult={widthmult})"
        )
        if name not in self.nodeGraph:
            return
        router_key = None
        if f"power_{name}" in self.named_rects:
            router_key = f"power_{name}"
        elif f"rail_{name}" in self.named_rects:
            router_key = f"rail_{name}"
        else:
            self.log.error(f"addPowerStrap: no ring or rail for {name}")
            return

        graph = self.nodeGraph.get(name)
        if graph is None:
            return
        if terminals:
            #- Strap only the named terminals. With a library that rings its
            #- devices, the body pin is the one worth strapping: it sits in
            #- the guard column, so the strap runs up inside the guard and
            #- crosses nothing, and one of them carries the whole guard
            #- network to the ring. The sources are already on the guard,
            #- see addPowerGuardConnection.
            rects = []
            for port in getattr(graph, "ports", []):
                inst = getattr(port, "parent", None)
                if inst is None or not inst.isInstance():
                    continue
                if getattr(port, "childName", "") not in terminals:
                    continue
                if not self._instance_matches_route_scope(inst, includeInstances=includeInstances, excludeInstances=excludeInstances):
                    continue
                rr = port.get(self._pinLayer()) if hasattr(port, "get") else None
                if rr is not None:
                    rects.append(rr)
        else:
            rects = self.getNodeAccessRects(
                name, self._pinLayer(), includeInstances=includeInstances,
                excludeInstances=excludeInstances, includeGroups=includeGroups)
            if len(rects) == 0:
                rects = graph.getRectangles(excludeInstances, includeInstances, "")
        if len(rects) == 0:
            self.log.error(f"addPowerStrap: no access rectangles on {name}")
            return

        routering = self.named_rects[router_key]
        rrect = routering.get(location)
        strapLayer = rrect.layer
        width = Rules.getInstance().get(strapLayer, "width") * widthmult

        from .cut import Cut
        vertical = location in ("top", "bottom")
        for r in rects:
            ct = None
            if r.layer != strapLayer:
                ct = self._fittedCut(r, strapLayer)
                if ct is None:
                    self.log.error(
                        f"addPowerStrap: no cut from {r.layer} to {strapLayer} fits the {name} pin")
                    continue

            #- the strap starts at the pin, so the via under it is covered,
            #- and stays inside the pin's own footprint rather than reaching
            #- over a neighbour. ``align`` decides where inside: a power pin
            #- can be wide enough to sit under a neighbouring signal pin's
            #- via stack, and a centred strap then lands a fraction of a
            #- micron from that stack's pad on the same layer. Pushing the
            #- strap to the far edge of its own pin buys that clearance
            #- without moving anything.
            #-
            #- None of that applies when the strap is on the pin's own
            #- layer. There is no via to clear, and the pin already fills
            #- its footprint on that layer, so necking down buys no room
            #- for anyone and only adds resistance and a notch where the
            #- narrow strap meets the wide pin. Same layer, then, the
            #- strap matches the port
            samelayer = ct is None
            if vertical:
                w = r.width() if samelayer else min(width, r.width())
                if samelayer:
                    x1 = int(r.x1)
                elif align == "left":
                    x1 = int(r.x1)
                elif align == "right":
                    x1 = int(r.x2 - w)
                else:
                    x1 = int(r.centerX() - w//2)
                cy = int(r.centerY())
                #- the cut follows the strap, otherwise an aligned strap
                #- leaves its own via uncovered out in the middle of the pin
                if ct:
                    cx = min(max(int(x1 + w//2 - ct.width()//2), int(r.x1)),
                             int(r.x2 - ct.width()))
                    ct.moveTo(cx, int(cy - ct.height()//2))
                if location == "top":
                    y1, y2 = cy, int(rrect.y2)
                else:
                    y1, y2 = int(rrect.y1), cy
                strap = Rect(strapLayer, x1, y1, int(w), int(y2 - y1))
            else:
                h = r.height() if samelayer else min(width, r.height())
                if samelayer:
                    y1 = int(r.y1)
                elif align == "left":
                    y1 = int(r.y1)
                elif align == "right":
                    y1 = int(r.y2 - h)
                else:
                    y1 = int(r.centerY() - h//2)
                cx = int(r.centerX())
                if ct:
                    cy = min(max(int(y1 + h//2 - ct.height()//2), int(r.y1)),
                             int(r.y2 - ct.height()))
                    ct.moveTo(int(cx - ct.width()//2), cy)
                if location == "right":
                    x1, x2 = cx, int(rrect.x2)
                else:
                    x1, x2 = int(rrect.x1), cx
                strap = Rect(strapLayer, x1, y1, int(x2 - x1), int(h))
            strap.net = name

            routering.add(strap)
            if ct:
                routering.add(ct)

    def addPowerGuardConnection(self, name:str, includeInstances:str="", excludeInstances:str="", terminals=("S",), bulk:str="B", layer:str="", widthmult:int=1):
        """Tie every device source on a power net to that device's own bulk
        guard ring, locally, on the layer the pins already live on.

        For a library that rings each device in its own tap, this is the
        whole power connection and there is nothing to strap. The source
        of a device whose source *is* the supply sits a fraction of a
        micron from the guard column beside it, on the same layer, and the
        guard is already continuous up and down the stack and tied left to
        right by the tap cells. So the connection is a short jog at the
        device's own row instead of a rail running the height of the
        column, and every layer above stays empty for signals.

        Contrast addPowerStrap, which is for cells that expose a pin and
        nothing else: it has to carry the net out to a ring, and whatever
        it crosses on the way is the caller's problem.

        Only devices that have both the power net on ``terminals`` and the
        same net on ``bulk`` are connected: a cascode whose source is an
        internal node is left alone for the signal router.
        """
        #- default to the technology's pin layer rather than to "M1"
        layer = layer or self._pinLayer()
        self.log.info(
            f"addPowerGuardConnection(name={name}, includeInstances={includeInstances}, excludeInstances={excludeInstances}, terminals={terminals}, bulk={bulk}, layer={layer})"
        )
        graph = self.nodeGraph.get(name)
        if graph is None:
            return

        sources, bulks = {}, {}
        for port in getattr(graph, "ports", []):
            inst = getattr(port, "parent", None)
            if inst is None or not inst.isInstance():
                continue
            if not self._instance_matches_route_scope(inst, includeInstances=includeInstances, excludeInstances=excludeInstances):
                continue
            child = getattr(port, "childName", "")
            if child in terminals:
                sources.setdefault(id(inst), []).append(port)
            elif child == bulk:
                bulks.setdefault(id(inst), []).append(port)

        made = 0
        for key, sports in sources.items():
            bports = bulks.get(key)
            if not bports:
                #- source on the supply but bulk somewhere else, or a cell
                #- with no guard of its own. Not ours to connect.
                continue
            for sp in sports:
                s = sp.get(layer) if hasattr(sp, "get") else None
                if s is None:
                    continue
                #- nearest guard, a device can be ringed on both sides
                best = None
                for bp in bports:
                    b = bp.get(layer) if hasattr(bp, "get") else None
                    if b is None:
                        continue
                    d = abs(b.centerX() - s.centerX())
                    if best is None or d < best[0]:
                        best = (d, b)
                if best is None:
                    continue
                b = best[1]
                #- centre to centre, so the jog starts inside the guard and
                #- ends inside the source rather than merely touching them
                x1, x2 = sorted((int(b.centerX()), int(s.centerX())))
                h = int(s.height()) * widthmult
                y1 = int(s.centerY() - h // 2)
                r = Rect(layer, x1, y1, x2 - x1, h)
                r.net = name
                self.add(r)
                made += 1
        if made == 0:
            self.log.warning(f"addPowerGuardConnection: nothing connected on {name}")

    def _fittedCut(self, rect, toLayer):
        """Largest cut between ``rect``'s layer and ``toLayer`` that fits
        inside ``rect``. A via wider than the pin it lands on reaches over
        whatever is next to it, which for a tightly packed transistor cell
        is another terminal."""
        from .cut import Cut
        best = None
        for h, v in ((2, 2), (1, 2), (2, 1), (1, 1)):
            ct = Cut.getInstance(rect.layer, toLayer, h, v)
            if ct is None:
                continue
            if ct.width() <= rect.width() and ct.height() <= rect.height():
                if best is None or (ct.width() * ct.height()) > (best.width() * best.height()):
                    best = ct
        return best

    def addRouteConnection(self, path:str, includeInstances:str, layer:str, location:str, options:str, routeTypeOverride:str="", excludeInstances:str="", includeGroups:str=""):
        self.log.info(f"addRouteConnection(path={path}, includeInstances={includeInstances}, layer={layer}, location={location}, options={options}, routeTypeOverride={routeTypeOverride}, excludeInstances={excludeInstances}, includeGroups={includeGroups})")
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
            rects = self.getNodeAccessRects(node, layer, includeInstances=includeInstances, excludeInstances=excludeInstances, includeGroups=includeGroups, options=options)
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
                        "excludeInstances": excludeInstances,
                        "includeGroups": includeGroups,
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

    def _runStackPycells(self):
        """Let every stack that ships a pycell route itself, before the
        parent routes anything.

        Opt-in by the existence of a `<STACKCELL>.py` beside the design,
        so a cell with no such file is untouched and every existing
        design behaves exactly as before. The built-in stack router is
        NOT run from here: it would add internal routing to every design
        that ever called addStack, which is not this method's business.
        """
        try:
            from .subcell import run_stack_pycells
        except Exception:
            return
        try:
            run_stack_pycells(self, log=self.log)
        except Exception as e:
            self.log.error(f"stack pycells: {e}")

    def _pinLayer(self):
        """The layer the cells put their pins on, from the technology.

        ROUTE.pinlayer. It was a literal "M1" in the power path, which
        is the sky130 answer and silently the wrong rect on any
        technology whose primitives present pins anywhere else -- and
        wrong quietly, because getNodeAccessRects just returns nothing
        and the strap is skipped with an error about a missing pin.
        """
        from .trackmap import TrackMap
        return TrackMap(self).pin_layer or "M1"

    def _metalStack(self):
        """The technology's metal layers, bottom up."""
        from .trackmap import TrackMap
        return TrackMap(self).metal_stack()

    def _layerAbove(self, layer):
        """The next metal up from `layer`, or None at the top."""
        stack = self._metalStack()
        if layer in stack:
            i = stack.index(layer)
            if i + 1 < len(stack):
                return stack[i + 1]
        return None

    def _topLayerRunning(self, direction):
        """The highest routing layer that runs `direction` ("v"/"h")."""
        from .trackmap import TrackMap
        tm = TrackMap(self)
        stack = tm.metal_stack()
        wanted = [l for l in stack if tm.directions.get(l) == direction]
        return wanted[-1] if wanted else (stack[-1] if stack else None)

    def addPowerRing(self, layer:str, name:str, location:str="rtbl", widthmult:int=1, spacemult:int=10):
        self.log.info(f"addPowerRing(layer={layer}, name={name}, location={location}, widthmult={widthmult}, spacemult={spacemult})")
        #- The ring is as wide as a via up off its OWN layer, which is
        #- what a rail has to be able to carry. Cut.getInstance("M3","M4")
        #- gave the right number for a sky130 M1 ring by coincidence and
        #- nothing anywhere else.
        above = self._layerAbove(layer)
        c = Cut.getInstance(layer, above, 2, 2) if above else None
        if c is None:
            mw = Rules.getInstance().get(layer, "width") * widthmult
        else:
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

    def addChannelRoute(self, layer:str, name:str, channel:str, track:int=0,
                        widthmult:int=1, key:str=None):
        """A RouteRing variant lying ACROSS the cell on a channel track.

        The bar spans the full extent of the top-level cell at the
        given track of a channel registered by addRoutingChannel,
        and takes the channel's own direction: a horizontal channel
        (between rows) gets the classic horizontal bar, a vertical
        channel (a column) gets a vertical one, with the drops of
        addRouteConnection turning to match. It registers as
        ``rail_<name>`` exactly like a ring side, so
        addPowerConnection stretches pins to it, and it trims the
        same way: call trimChannelRoute after the connections are in
        and the bar pulls back to the outermost one.
        """
        self.log.info(f"addChannelRoute(layer={layer}, name={name}, "
                      f"channel={channel}, track={track})")
        coord = self.channelTrackCoord(channel, track)
        if coord is None:
            return None
        ch = self.routingChannel(channel)
        horizontal = True if ch is None else bool(ch[2])
        mw = Rules.getInstance().get(layer, "width") * widthmult
        from .routering import ChannelRoute
        if horizontal:
            cr = ChannelRoute(layer, name, int(self.x1), int(self.x2),
                              int(coord), int(mw))
        else:
            cr = ChannelRoute(layer, name, int(self.y1), int(self.y2),
                              int(coord), int(mw), horizontal=False)
        #- keyed: one net may own several bars -- a segment per track,
        #- bridged where the traffic wants -- and each is addressed by
        #- its key. The unkeyed call keeps the ring-compatible name.
        key = key or name
        if key == name:
            self.updatePort(name, cr.getDefault())
        self.named_rects[f"rail_{key}"] = cr
        self.add(cr)
        return cr

    def addChannelBridge(self, name:str, key_a:str, key_b:str,
                         layer:str="M2", x:int=None):
        """Join two ChannelRoutes of one net inside the channel.

        A vertical on ``layer`` between the two bars, cut at each. By
        default it stands at the middle of the bars' x overlap; pass
        ``x`` (e.g. a channelTrackCoord of a vertical channel) to
        place it. On a layer other than the bars' own it crosses any
        bar between them; on the same layer it must not have to.
        """
        a = self.named_rects.get(f"rail_{key_a}")
        b = self.named_rects.get(f"rail_{key_b}")
        if a is None or b is None:
            self.log.error(f"addChannelBridge: missing rail {key_a} or {key_b}")
            return
        ra, rb = a.getDefault(), b.getDefault()
        if x is None:
            lo = max(ra.x1, rb.x1)
            hi = min(ra.x2, rb.x2)
            if lo > hi:
                self.log.error(f"addChannelBridge: bars of {name} do not overlap; pass x")
                return
            x = (lo + hi) / 2
        rules = Rules.getInstance()
        w = rules.get(layer, "width")
        from .rect import VerticalRectangleFromTo
        from .cut import Cut
        v = VerticalRectangleFromTo(layer, int(x - w / 2),
                                    int(ra.centerY()), int(rb.centerY()),
                                    int(w))
        v.net = name
        a.add(v)
        for rail, ring in ((ra, a), (rb, b)):
            if layer == rail.layer:
                continue
            #- the largest array the rail can hold, not a lone cut. A
            #- 1x1 between two supply rings is one contact carrying a
            #- ring's current, and it was typed here rather than chosen
            ct = self._fittedCut(rail, layer)
            if ct is None:
                ct = Cut.getInstance(layer, rail.layer, 1, 1)
            if ct is None:
                ct = Cut.getInstance(rail.layer, layer, 1, 1)
            if ct is not None:
                ct.moveCenter(int(x), int(rail.centerY()))
                ring.add(ct)
        return v

    def addRailConnection(self, name:str, includeInstances:str="",
                          location:str="t", layer:str="M2",
                          excludeInstances:str="", align:str="center",
                          cuts:int=2, key:str=None, pin_cut:bool=True,
                          cut_shape:str="auto"):
        """Drop a net's pins onto its rail -- ChannelRoute or ring.

        NOT addRouteConnection, which is a DIFFERENT method with a
        different signature (path, includeInstances, layer, location,
        options) that classic pycells call. This one was named that
        too, and since Python keeps the second definition of a name it
        silently shadowed the first: every existing caller had its
        layer read as a location and its location as a layer, so the
        drops never landed and the net came out open. LELOTEMP_CMP
        went from LVS clean to ten split nets on that alone.

        The signal sibling of addPowerConnection: where that stretches
        the pin's own rect on the pin layer (right for a supply pin
        facing its ring across guard), this drops a routing-width
        vertical on ``layer`` from each selected pin to the rail, with
        a via stack at the pin and one at the rail. ``align`` picks
        where on the pin the drop stands -- left, center, right -- 
        which is the dial that separates nets whose pins share a
        column.
        """
        rr_key = None
        for k in (f"rail_{key}" if key else None,
                  f"rail_{name}", f"power_{name}"):
            if k and k in self.named_rects:
                rr_key = k
                break
        if rr_key is None:
            self.log.error(f"addRouteConnection: no rail for {name}")
            return
        routering = self.named_rects[rr_key]
        rail = routering.get(location)
        if rail is None:
            return
        #- ONE drop per instance, on the instance's PORT for the net:
        #- the port is the published contract, where the access-rect
        #- list also carries duplicate subports, one of which stood at
        #- a stale position and dropped a via stack into a foreign bar
        #- (measured: the whole powerdown family merged).
        rects = []
        import re as _re
        for inst in self.iterInstances():
            inm = getattr(inst, "instanceName", "")
            if includeInstances and not _re.search(includeInstances, inm):
                continue
            if excludeInstances and _re.search(excludeInstances, inm):
                continue
            p = getattr(inst, "instancePorts", {}).get(name)
            r = p.get() if p is not None and hasattr(p, "get") else None
            if r is not None:
                rects.append(r)
        if not rects:
            rects = self.getNodeAccessRects(name, self._pinLayer(),
                                            includeInstances=includeInstances,
                                            excludeInstances=excludeInstances)
        rules = Rules.getInstance()
        w = rules.get(layer, "width")
        from .cut import Cut
        from .rect import VerticalRectangleFromTo, HorizontalRectangleFromTo
        if not hasattr(self, "_drop_rects"):
            self._drop_rects = []
        #- the drop turns with the rail: a horizontal bar takes
        #- vertical drops (align picks the x on the pin), a vertical
        #- bar takes horizontal ones (align top/bottom/center picks
        #- the y)
        if rail.height() > rail.width():
            for r in rects:
                if align == "top":
                    y = r.y2 - w / 2
                elif align == "bottom":
                    y = r.y1 + w / 2
                else:
                    y = r.centerY()
                drop = HorizontalRectangleFromTo(layer, int(r.centerX()),
                                                 int(rail.centerX()),
                                                 int(y - w / 2), int(w))
                drop.net = name
                routering.add(drop)
                self._drop_rects.append(drop)
                ends = ((r, r.centerX(), False),
                        (rail, rail.centerX(), True))
                if not pin_cut:
                    ends = ends[1:]
                for target, xc, at_rail in ends:
                    if layer == target.layer:
                        continue
                    cs = Cut.getCutsForRects(layer, [target.getCopy()],
                                             cuts, 1, True)
                    if cs:
                        ct = cs[0]
                        half = ct.height() / 2
                        if at_rail:
                            yc = y
                        elif align == "top":
                            yc = target.y2 - half
                        elif align == "bottom":
                            yc = target.y1 + half
                        else:
                            lo, hi = target.y1 + half, target.y2 - half
                            yc = y if lo > hi else min(max(y, lo), hi)
                        ct.moveCenter(int(xc), int(yc))
                        routering.add(ct)
            return
        for r in rects:
            if align == "left":
                x = r.x1 + w / 2
            elif align == "right":
                x = r.x2 - w / 2
            else:
                x = r.centerX()
            drop = VerticalRectangleFromTo(layer, int(x - w / 2),
                                           int(r.centerY()),
                                           int(rail.centerY()), int(w))
            drop.net = name
            routering.add(drop)
            #- pin_cut=False lands the drop on metal the subcell
            #- already provides at the pin (its own via stack); a
            #- second stack there is a partial via overlap, which the
            #- rules forbid. Cuts go through getCutsForRects: two
            #- cuts along the target's long side for reliability,
            #- auto-shrunk where a narrow tab only fits one.
            self._drop_rects.append(drop)
            ends = ((r, r.centerY(), False),
                    (rail, rail.centerY(), True))
            if not pin_cut:
                ends = ends[1:]
            for target, yc, at_rail in ends:
                if layer == target.layer:
                    continue
                #- "auto" asks for cuts along the target's long side
                #- and lets getCutsForRects swap them to the rect's
                #- aspect. That is right until the pad it makes is
                #- what collides: a 2x1 on a horizontal rail is 8.8 um
                #- wide over a 3 um wire and reaches into whatever
                #- runs beside it. "v"/"h" force the direction so the
                #- SAME two cuts occupy the axis that has room.
                hc, vc = (1, cuts) if cut_shape == "v" else (cuts, 1)
                cs = Cut.getCutsForRects(layer, [target.getCopy()],
                                         hc, vc, True,
                                         forceShape=cut_shape in ("v", "h"))
                if cs:
                    ct = cs[0]
                    half = ct.width() / 2
                    if at_rail:
                        #- on the rail the cut starts under the wire
                        #- and slides along the bar away from foreign
                        #- drops crossing the trunk -- their vertical
                        #- and this cut's pad share a layer.
                        xc = self._avoidForeignDrops(ct, x, yc, name,
                                                     (layer,
                                                      target.layer))
                    elif align == "left":
                        #- the cut follows the align: a left-aligned
                        #- wire with a centered two-cut pad overhangs
                        #- the pin edge into the neighbouring lane
                        #- (li.3, measured). Flush against the edge
                        #- the wide pad still covers the wire.
                        xc = target.x1 + half
                    elif align == "right":
                        xc = target.x2 - half
                    else:
                        lo, hi = target.x1 + half, target.x2 - half
                        xc = x if lo > hi else min(max(x, lo), hi)
                    ct.moveCenter(int(xc), int(yc))
                    routering.add(ct)

    def _avoidForeignDrops(self, ct, x:float, yc:float, net:str,
                           layers):
        """Slide a rail cut along the bar until its pads clear every
        other net's drop vertical crossing the trunk at that height.

        The window is bounded by pad-covers-wire: the wire must stay
        inside the cut's pad or the slide opens the net it serves."""
        rules = Rules.getInstance()
        half = ct.width() / 2
        w = rules.get(layers[0], "width")
        slack = max(0, half - w / 2)
        hh = ct.height() / 2
        obstacles = []
        for o in getattr(self, "_drop_rects", []):
            if getattr(o, "net", None) == net or o.layer not in layers:
                continue
            if o.y1 > yc + hh or o.y2 < yc - hh:
                continue
            obstacles.append((o, rules.get(o.layer, "space")))

        def clear(xc):
            for o, sp in obstacles:
                if xc + half + sp > o.x1 and xc - half - sp < o.x2:
                    return False
            return True

        if clear(x) or not obstacles:
            return x
        step = 200
        d = step
        while d <= slack:
            for xc in (x - d, x + d):
                if clear(xc):
                    return xc
            d += step
        return x

    def trimChannelRoute(self, name:str, ends:str="lr"):
        cr = self.named_rects.get(f"rail_{name}")
        if cr is not None and hasattr(cr, "trim"):
            cr.trim(ends)
            #- the port took a copy of the untrimmed bar at creation;
            #- refresh it or the cell advertises a full-width pin the
            #- metal no longer backs
            self.updatePort(name, cr.getDefault())

    def addRouteGroup(self, net: str) -> "RouteGroup":
        """Return a chainable ``RouteGroup`` builder for ``net``.

        See ``cicpy.core.routegroup`` for usage. The builder composes the
        existing routing primitives — calling this and not invoking any
        builder methods is a no-op."""
        return RouteGroup(self, net)

    def getInstanceFromInstanceName(self, instanceName:str):
        for i in self.iterInstances():
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
        self.guiHierarchy = o.get("cellgroups", o.get("guiHierarchy", [])) or []

    def _shortSignature(self):
        """Set of net-name frozensets, one per multi net short component."""
        result = self.checkConnectivity()
        return {frozenset(s.get("nets", [])) for s in result.get("shorts", [])
                if len(s.get("nets", [])) > 1}

    def route(self):
        """Route all routes in this layout cell.

        With strict_route set, connectivity is checked after every single
        route, and a route that introduces a new short stops the flow on
        the spot with the offending command and callsite in the message.
        Finding the guilty route at the end is possible but painful, so
        the default of the sch2mag --strict flow is to not proceed when
        something is wrong.
        """
        strict = getattr(self, "strict_route", False)
        baseline = self._shortSignature() if strict else set()
        if strict and baseline:
            nets = "; ".join(",".join(sorted(s)) for s in baseline)
            raise RuntimeError(
                f"placement is already shorted before routing: {nets}. "
                "Fix the placement first, a route check cannot pass on top "
                "of a shorted placement")
        for r in self.routes:
            if r.isRoute() and not getattr(r, '_pre_routed', False):
                r.route()
                if strict:
                    now = self._shortSignature()
                    fresh = now - baseline
                    if fresh:
                        nets = "; ".join(",".join(sorted(s)) for s in fresh)
                        cmd = getattr(r, "debug_command", "") or getattr(r, "name", "?")
                        site = getattr(r, "debug_callsite", "")
                        raise RuntimeError(
                            f"route created a short ({nets}): {cmd}"
                            + (f" at {site}" if site else ""))

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
            #- A power sheet spans the cell top to bottom, so it belongs
            #- on the highest layer the technology runs VERTICALLY. That
            #- is M4 in sky130 here, which is what this used to say
            #- outright.
            sheet = self._topLayerRunning("v")
            if sheet is None:
                self.log.warning(
                    f"addPowerRoute({net}): the technology declares no "
                    f"vertical routing layer; not routing")
                return
            cuts = Cut.getCutsForRects(sheet, rects, 2, 1)
            rp = None

            if len(cuts) > 0:
                r_bound = Cell.calcBoundingRectFromList(cuts, False)
                r_bound.setTop(self.top())
                r_bound.setBottom(self.bottom())
                for cut in cuts:
                    self.add(cut)
                rp = Rect(sheet, r_bound.x1, r_bound.y1, r_bound.width(), r_bound.height())
            else:
                r_bound = Cell.calcBoundingRectFromList(rects, False)
                r_bound.setTop(self.top())
                r_bound.setBottom(self.bottom())
                rp = Rect(sheet, r_bound.x1, r_bound.y1, r_bound.width(), r_bound.height())

            if rp:
                self.add(rp)
                if net in self.ports:
                    p = self.ports[net]
                    p.set(rp)

    def findRectanglesByNode(self,node:str,filterChild:str=None,matchInstance:str=None):
        rects = list()
        for i in self.iterInstances():
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

        if("noPowerRoute" in o):
            self.noPowerRoute = o["noPowerRoute"]

        if("boundarIgnoreRouting" in o):
            self.boundaryIgnoreRouting = o["boundaryIgnoreRouting"]

        self.guiHierarchy = o.get("cellgroups", o.get("guiHierarchy", [])) or []

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
            elif(cl in ("Cell", "Route", "RouteRing", "ChannelRoute", "Guard", "OrthogonalLayerRoute", "cIcCore::Route", "cIcCore::RouteRing", "cIcCore::Guard", "cIcCore::Cell", "cIcCore::LayoutCell")):
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

    def addConnectivityRoute(self,layer,regex, routeType, options, cuts, excludeInstances, includeInstances, includeGroups=""):
        #- named channels work here too. They did not, and the failure
        #- was silent: the option string was passed through untouched,
        #- so vchannel/vtrack looked accepted and every route in a column
        #- still took the spine its own pins implied. Five ladder nets
        #- asked for five tracks and landed on one.
        options = self._resolveChannelOptions(options)
        options = self._withCuts(options, cuts)
        self.log.info(f"addConnectivityRoute(layer={layer}, regex={regex}, routeType={routeType}, options={options}, cuts={cuts}, excludeInstances={excludeInstances}, includeInstances={includeInstances}, includeGroups={includeGroups})")
        prefer_anymetal = bool(re.search(r"anymetal(,|\s+|$)", options or ""))
        for node in list(self.nodeGraphList):
            if not re.search(regex, node):
                continue
            log = logging.getLogger("LayoutCell")
            log.info(f"addConnectivityRoute: node={node}")
            g = self.nodeGraph.get(node)
            if g is None:
                continue
            rects = self.getNodeAccessRects(node, layer, includeInstances=includeInstances, excludeInstances=excludeInstances, includeGroups=includeGroups, anymetal=prefer_anymetal, options=options)
            if len(rects) == 0:
                self.log.error(f"Could not find rectangles on {node} {regex} {len(rects)}")
                continue
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
                    "includeGroups": includeGroups,
                    "node": node,
                })
                log.info(f"addConnectivityRoute: r={r}")
                self.add(r)
            except Exception as e:
                log.error(f"addConnectivityRoute: Exception={e}")
                for rr in rects:
                    self.add(rr.getCopy(layer))

    def addOrthogonalRouteFromRects(self, net, verticalLayer, horizontalLayer, rects, options="", cuts=2):
        self.log.info(
            f"addOrthogonalRouteFromRects(net={net}, verticalLayer={verticalLayer}, horizontalLayer={horizontalLayer}, options={options}, cuts={cuts}, rects={len(rects or [])})"
        )
        if not rects:
            self.log.error(f"Could not find rectangles on {net} explicit rect list")
            return None
        from .route import OrthogonalLayerRoute
        r = OrthogonalLayerRoute(net, verticalLayer, horizontalLayer, rects, options, cuts=cuts)
        self._annotateRoute(r, "addOrthogonalRouteFromRects", {
            "net": net,
            "verticalLayer": verticalLayer,
            "horizontalLayer": horizontalLayer,
            "options": options,
            "cuts": cuts,
            "rect_count": len(rects or []),
        })
        self.add(r)
        r.route()
        return r

    def path(self, net, layer, start=None, stop=None, options="",
             includeInstances="", excludeInstances="",
             includeGroups=""):
        """A route told as a story: anchored steps, spelled `~`.

        The twelfth shape, beside the eleven ASCII ones -- additive, so
        nothing that works today can change. Use it where the canned
        shapes ran out, which is exactly the set of nets the maze
        router currently abandons as "not a shape route.py can draw".

            p = cell.path("VBP", "M1", startRects, stopRects)
            p.start(); p.up(); p.movex(p.tab_lane()); p.trunk()
            p.down(); p.end()

        Registered and routed like any other route -- see core/path.py.
        """
        from .path import Path
        if start is None and stop is None:
            #- SCOPED like addConnectivityRoute: the same collector, the
            #- same include/exclude, so a story decomposes a net the way
            #- a design already does -- one route for the gates, one for
            #- the drains -- instead of forcing every pin onto one rail.
            stop = self.getNodeAccessRects(
                net, layer, includeInstances=includeInstances,
                excludeInstances=excludeInstances,
                includeGroups=includeGroups, options=options)
            if not stop:
                self.log.error(f"path: no rectangles on {net}")
        p = Path(net, layer, start, stop, options)
        p.layoutcell = self
        self.add(p)
        return p

    def addRoutingChannel(self, name, lo, hi, horizontal=True):
        """Name the gap the placement opened, so routes can aim at it.

        A route may not carry coordinates: the same pycell has to hold
        for another technology and for a resize, where every number
        moves. What does not move is the *structure* -- there is a
        channel between these two rows, and a net crosses on the third
        track of it. So the placement registers the gap it just made,
        in whatever units that technology produced, and routes refer to
        it by name and index.

        The registration itself carries the only numbers, and they come
        from the placement that just ran, so they are whatever this
        technology produced.

        Call from afterPlace with the group extents::

            channel_lo = nmos.y2
            channel_hi = pmos.y1
            layout.addRoutingChannel("mid", channel_lo, channel_hi)

        and route with ``"channel=mid,ctrack=3"``.
        """
        if not hasattr(self, "_routing_channels"):
            self._routing_channels = {}
        self._routing_channels[name] = (lo, hi, horizontal)
        self.log.info(
            f"addRoutingChannel({name}, {lo}, {hi}, "
            f"{'horizontal' if horizontal else 'vertical'})")
        return self

    def routingChannel(self, name):
        return getattr(self, "_routing_channels", {}).get(name)

    def channelTrackCoord(self, name, index, layer=None):
        """The coordinate of track `index` inside a named channel.

        A TRACK IS ONE LEGAL LANE: the pitch is `width + space` for the
        metal that will ride it, so track N and track N+1 are the
        closest two wires the technology allows and consecutive indices
        are consecutive lanes.

        It used to be `ROUTE.horizontalgrid`/`verticalgrid`, which is
        the SEARCH grid and finer than a lane -- the maze router says
        so itself (`mazerouter.clearance`: "THE TRACK GRID IS FINER
        THAN THAT... Two nets on ADJACENT tracks abut exactly and
        short"). So a design could not use consecutive indices, and
        both hierarchical designs had been hand-compensating: every
        `track:` in them was even, with a comment explaining that
        channel tracks go two apart. On a horizontal channel two apart
        was 8000 against a legal 6000 and wasted a third of every lane.

        `layer` names the metal when the caller knows it. Otherwise the
        widest lane in the stack is used, so an index is legal for
        whatever ends up riding it -- a channel carries bars and drops
        on several layers, and a track that is only legal for the
        thinnest of them is a short waiting for the design to change
        one `bar_layer`.
        """
        ch = self.routingChannel(name)
        if ch is None:
            self.log.error(f"no routing channel named {name}")
            return None
        lo, hi, horizontal = ch
        pitch = self._lanePitch(layer)
        n = max(1, int((hi - lo) // pitch))
        if index >= n:
            self.log.warning(
                f"channel {name} has {n} tracks, asked for {index}")
        return lo + (index + 0.5) * pitch

    def _lanePitch(self, layer=None):
        """One legal lane, centre to centre: `width + space`.

        The ruler the framework already uses where it gets this right
        -- `mazerouter.clearance()` is width + space, `via_is_free`'s
        margin is space + width//2. Without `layer`, the widest lane in
        the metal stack, which is legal for every layer.
        """
        rules = Rules.getInstance()

        def lane(l):
            return int(rules.get(l, "width")) + int(rules.get(l, "space"))

        if layer:
            try:
                return lane(layer)
            except Exception:
                pass
        widest = 0
        for l in self._metalStack():
            try:
                widest = max(widest, lane(l))
            except Exception:
                continue
        if widest:
            return widest
        #- no metal stack to read: the search grid is the only number
        #- left, and it is at least a number
        return int(rules.get("ROUTE", "horizontalgrid"))

    @staticmethod
    def _withCuts(options, cuts):
        """Say the caller's cut count in the options, where route.py
        reads it.

        `cuts` reached the debug annotation and nothing else -- it was
        never passed to Route -- so every design that typed a number
        here was writing a comment, and route.py's own default (2x1)
        decided. The parameter says what it means now; an explicit
        `<N>cuts` in the options still wins, because that is the
        narrower statement.
        """
        if not cuts or re.search(r"\d+cuts", options or ""):
            return options
        return (options + "," if options else "") + f"{int(cuts)}cuts"

    def _resolveChannelOptions(self, options):
        """Turn channel names into this run's coordinates.

        A route names structure, not numbers::

            "hchannel=mid,htrack=5"     the bar, in the gap between rows
            "vchannel=bias,vtrack=2"    the trunk, inside a column

        and both may appear together. The numbers are computed here,
        where the placement is known, so the pycell survives a resize
        and a change of technology. ``channel=``/``ctrack=`` is accepted
        as a shorthand when the channel's own direction says which one
        is meant.
        """
        if not options:
            return options
        import re as _re
        for prefix, tname in (("hchannel", "htrack"),
                              ("vchannel", "vtrack"),
                              ("channel", "ctrack")):
            m = _re.search(prefix + r"=([A-Za-z0-9_]+)", options)
            if not m:
                continue
            name = m.group(1)
            t = _re.search(tname + r"=(-?\d+)", options)
            index = int(t.group(1)) if t else 0
            options = _re.sub(prefix + r"=[A-Za-z0-9_]+,?", "", options)
            options = _re.sub(tname + r"=-?\d+,?", "", options)
            coord = self.channelTrackCoord(name, index)
            if coord is None:
                continue
            ch = self.routingChannel(name)
            key = "bandy" if ch[2] else "trunkx"
            options = options.strip(",")
            options = (options + "," if options else "") + f"{key}{int(coord)}"
        return options.strip(",")

    def addChannelConnection(self, verticalLayer, horizontalLayer, regex,
                             channel, track, cuts=2, includeInstances="",
                             excludeInstances="", options=""):
        """Connect pins to a track of a named routing channel.

        The channel analog of addPowerConnection to a ring: the
        channel is registered by addRoutingChannel, the track is an
        index on it, and each call drops the selected pins onto that
        track. Successive calls for the SAME net on the same track
        extend one shared bar across the union of their spans, so a
        net can be attached group by group -- the pattern that
        otherwise takes two orthogonal routes whose bars only meet if
        their pin spans happen to overlap.
        """
        opts = f"hchannel={channel},htrack={track}"
        if options:
            opts += "," + options
        r = self.addOrthogonalConnectivityRoute(
            verticalLayer, horizontalLayer, regex, opts, cuts,
            excludeInstances, includeInstances)
        #- the shared bar: remember this call's span and pave the
        #- union, so the next call's bar lands on the same metal
        coord = self.channelTrackCoord(channel, track)
        if coord is None:
            return r
        rects = self.getNodeAccessRects(regex.strip("^$"), verticalLayer,
                                        includeInstances=includeInstances,
                                        excludeInstances=excludeInstances)
        if not rects:
            return r
        x1 = min(rr.x1 for rr in rects)
        x2 = max(rr.x2 for rr in rects)
        if not hasattr(self, "_channel_bars"):
            self._channel_bars = {}
        key = (channel, int(track), regex)
        if key in self._channel_bars:
            ox1, ox2 = self._channel_bars[key]
            x1, x2 = min(x1, ox1), max(x2, ox2)
        self._channel_bars[key] = (x1, x2)
        rules = Rules.getInstance()
        hw = rules.get(horizontalLayer, "width")
        bar = Rect(horizontalLayer, int(x1), int(coord - hw / 2),
                   int(x2 - x1), int(hw))
        bar.net = regex.strip("^$")
        self.add(bar)
        return r

    def addOrthogonalConnectivityRoute(self, verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, includeInstances, includeGroups=""):
        options = self._resolveChannelOptions(options)
        options = self._withCuts(options, cuts)
        self.log.info(
            f"addOrthogonalConnectivityRoute(verticalLayer={verticalLayer}, horizontalLayer={horizontalLayer}, regex={regex}, options={options}, cuts={cuts}, excludeInstances={excludeInstances}, includeInstances={includeInstances}, includeGroups={includeGroups})"
        )
        for node in list(self.nodeGraphList):
            if not re.search(regex, node):
                continue
            log = logging.getLogger("LayoutCell")
            log.info(f"addOrthogonalConnectivityRoute: node={node}")
            g = self.nodeGraph.get(node)
            if g is None:
                continue
            # Use whatever layer the port lives on; the route engine adds
            # the cuts up to verticalLayer/horizontalLayer.
            rects = self.getNodeAccessRects(node, verticalLayer, includeInstances=includeInstances, excludeInstances=excludeInstances, includeGroups=includeGroups, options=options)
            if len(rects) == 0:
                self.log.error(f"Could not find rectangles on {node} {regex} {len(rects)}")
                continue
            #- accessLayer=X: the pin already carries same-net metal on
            #- X (a subcell's own rail pad), so the route attaches
            #- there instead of stacking from the pin layer -- whose
            #- cut would partially overlap the subcell's own cut,
            #- which the via rules forbid.
            m = re.search(r"accessLayer=(\w+)", options or "")
            if m:
                rects = [r.getCopy(m.group(1)) for r in rects]
            try:
                from .route import OrthogonalLayerRoute
                r = OrthogonalLayerRoute(node, verticalLayer, horizontalLayer, rects, options, cuts=cuts)
                self._annotateRoute(r, "addOrthogonalConnectivityRoute", {
                    "verticalLayer": verticalLayer,
                    "horizontalLayer": horizontalLayer,
                    "regex": regex,
                    "options": options,
                    "cuts": cuts,
                    "excludeInstances": excludeInstances,
                    "includeInstances": includeInstances,
                    "includeGroups": includeGroups,
                    "node": node,
                })
                log.info(f"addOrthogonalConnectivityRoute: r={r}")
                self.add(r)
                r.route()
            except Exception as e:
                log.error(f"addOrthogonalConnectivityRoute: Exception={e}")
                for rr in rects:
                    self.add(rr.getCopy(verticalLayer))

    def addPortOnEdge(self,layer,node,location,routeType, options):
        self.log.info(f"addPortOnEdge(layer={layer}, node={node}, location={location}, routeType={routeType}, options={options})")
        if node not in self.ports:
            self.log.error(f"{node} not a port")
            return
        p = self.ports[node]
        if not getattr(p, "routeLayer", None) and getattr(p, "layer", ""):
            p.routeLayer = p.layer
        if not getattr(p, "pinLayer", None) and getattr(p, "routeLayer", ""):
            p.pinLayer = Port._resolve_pin_layer(p.routeLayer)
        r = p.get()
        if not r:
            self.log.error("no port rectangle")
            return
        rp = r.getCopy(layer)
        rules = Rules.getInstance()
        offset_tracks = 0
        if options:
            m = re.search(r"offset_track([+-]?\d+)", options)
            if m:
                offset_tracks = int(m.group(1))
        if(location == "bottom"):
            rp.moveTo(rp.x1,self.y1)
            if offset_tracks != 0 and rules is not None:
                rp.translate(offset_tracks * rules.get("ROUTE", "horizontalgrid"), 0)
        elif (location == "top"):
            rp.moveTo(rp.x1,self.y2-rp.height())
            if offset_tracks != 0 and rules is not None:
                rp.translate(offset_tracks * rules.get("ROUTE", "horizontalgrid"), 0)
        elif (location == "right"):
            rp.moveTo(self.x2 - r.width(),rp.y1)
            if offset_tracks != 0 and rules is not None:
                rp.translate(0, offset_tracks * rules.get("ROUTE", "verticalgrid"))
        elif (location == "left"):
            rp.moveTo(self.x1,rp.y1)
            if offset_tracks != 0 and rules is not None:
                rp.translate(0, offset_tracks * rules.get("ROUTE", "verticalgrid"))
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
            p.set(rp)
        except Exception as e:
            self.log.error(f"addPortOnEdge: Failed to create route for node '{node}': {e}. Adding rect directly.")
            self.add(rp)
            p.set(rp)

    def promoteInstancePort(self, node, instanceRegex, location, layer,
                            excludeInstances=""):
        """Carry a SUBCELL's port out to this cell's edge, as a pin.

        `addPortOnEdge` does this for a net that is already one of this
        cell's ports. The net that needs it most is not: a powerdown
        signal lives deep inside a finished subcell, and the parent has
        to present it at an edge before anything above can reach it.
        That was hand-drawn geometry -- a Rect for the riser, a 1x1
        Cut, a pad sized by a literal, an attach point 2400 off the
        pin's left edge -- in the one design that needed it.

        Every number here comes from the technology instead:

        - the CUT is the largest that fits the pin (`_fittedCut`), so
          the rule against 1x1 vias holds here too;
        - the PAD on each intermediate layer is the minimum area that
          layer demands, because a bare cut pad is under it;
        - the ATTACH POINT is `space + width/2` in from the end of a
          WIDE pin. Mid-bar, the cut pad's overhang lands a fraction of
          a lane from the neighbouring track's bar (met3.2, measured);
          a pin no wider than a pad is its own only landing and is
          taken at its centre.

        The riser runs on `layer` from the pin to `location` ("top",
        "bottom", "left", "right"), and the rect at the edge becomes
        this cell's port for `node`.
        """
        from .cut import Cut
        from .rect import Rect
        rules = Rules.getInstance()
        made = 0
        for inst in self.iterInstances():
            nm = getattr(inst, "instanceName", "") or ""
            if not re.search(instanceRegex, nm):
                continue
            if excludeInstances and re.search(excludeInstances, nm):
                continue
            pt = (getattr(inst, "instancePorts", None) or {}).get(node)
            r = pt.get() if pt is not None else None
            if r is None:
                continue

            w = int(rules.get(layer, "width"))
            #- in from the END of a wide pin, not its middle
            reach = int(rules.get(r.layer, "space")) + \
                int(rules.get(r.layer, "width")) // 2
            pad = self._minAreaPad(layer)
            if int(r.x2 - r.x1) > 2 * pad:
                cx = int(r.x1) + reach
            else:
                cx = int(r.centerX())
            cy = int(r.centerY())

            horizontal = location in ("left", "right")
            if location == "top":
                lo, hi = cy - w, int(self.y2)
            elif location == "bottom":
                lo, hi = int(self.y1), cy + w
            elif location == "right":
                lo, hi = cx - w, int(self.x2)
            else:
                lo, hi = int(self.x1), cx + w
            if horizontal:
                riser = Rect(layer, lo, cy - w, hi - lo, 2 * w)
            else:
                riser = Rect(layer, cx - w, lo, 2 * w, hi - lo)
            riser.setNet(node)
            self.add(riser)

            ct = (self._fittedCut(r, layer)
                  or Cut.getInstance(r.layer, layer, 1, 1)
                  or Cut.getInstance(layer, r.layer, 1, 1))
            if ct is not None:
                ct.moveCenter(cx, cy)
                self.add(ct)

            #- magic refuses a PARTIAL overlap of top-level geometry on
            #- a subcell's on the same layer, and covering the pin
            #- EXACTLY is not enough: a via that lands on a pin is
            #- wider than the pin (a 1x1 M1-M5 stack is 4800 against a
            #- 3200 tab), so its own enclosure is top-level metal
            #- hanging over the subcell's edge -- which is the partial
            #- overlap, one step out. The cover is the union of the pin
            #- and the via, so the subcell's shape is wholly inside it.
            if ct is not None and (r.layer == layer
                                   or r.layer == self._pinLayer()):
                ux1 = min(int(r.x1), int(ct.x1))
                uy1 = min(int(r.y1), int(ct.y1))
                ux2 = max(int(r.x2), int(ct.x2))
                uy2 = max(int(r.y2), int(ct.y2))
                cov = Rect(r.layer, ux1, uy1, ux2 - ux1, uy2 - uy1)
                cov.setNet(node)
                self.add(cov)
            #- the intermediate layers' own pads: a via stack leaves a
            #- cut-sized shape on each, and a cut-sized shape is under
            #- the minimum area every one of them asks for
            for mid in self._layersBetween(r.layer, layer):
                p = self._minAreaPad(mid)
                mp = Rect(mid, cx - p, cy - p, 2 * p, 2 * p)
                mp.setNet(node)
                self.add(mp)

            #- the EDGE is the pin the level above reaches
            if horizontal:
                px = int(self.x1) if location == "left" else int(self.x2) - 4 * w
                pin = Rect(layer, px, cy - w, 4 * w, 2 * w)
            else:
                py = int(self.y1) if location == "bottom" else int(self.y2) - 4 * w
                pin = Rect(layer, cx - w, py, 2 * w, 4 * w)
            pin.setNet(node)
            self.updatePort(node, pin)
            made += 1
        if not made:
            self.log.warning(f"promoteInstancePort: no instance matching "
                             f"{instanceRegex} exposes {node}")
        return self

    def _minAreaPad(self, layer):
        """Half the side of the smallest square meeting the layer's
        minimum area, falling back to its width when the technology
        states no area rule."""
        rules = Rules.getInstance()
        w = int(rules.get(layer, "width"))
        try:
            area = int(rules.get(layer, "area"))
        except Exception:
            return w
        side = int(math.ceil(math.sqrt(area)))
        return max(w, (side + 1) // 2)

    def _layersBetween(self, a, b):
        """The metals strictly between `a` and `b` in the stack."""
        stack = self._metalStack()
        if a not in stack or b not in stack:
            return []
        i, j = sorted((stack.index(a), stack.index(b)))
        return stack[i + 1:j]

    def _runSelfMethod(self,name,args=()):
        if(hasattr(self,name)):
            self.log.info("Running " + name  + " with "+",".join(map(str,args)))
            getattr(self,name)(*args)
        else:
            self.log.warning(f"Could not find method {name} on {self.name}")


    def _runIfHas(self,module,method,args=()):
        if(hasattr(module,method)):
            fn = getattr(module,method)
            self.log.info("Running " + method + " from " + self.name + ".py")
            fn(self,*args)
            return True
        else:
            return False



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
        self._runIfHas(module,method,*args)



    def hierarchy(self):
        """Build the cells this one is MADE OF, before it is placed.

        A flat cell is made of primitives and does nothing here. A cell
        that declares a decomposition splits its own netlist, builds a
        LayoutCell per part and registers each in the design ahead of
        itself -- so by the time place() runs, the instances it is
        about to place resolve to cells built moments ago in this same
        process. See SidecarCell.hierarchy.

        HERE, and not in readFromSpice: `dirname`, the place_* knobs
        and the default pycell are all set AFTER the read (cic.py), so
        a subcell built at read time inherits none of them and cannot
        find its own hooks. layout() is one line later and has
        everything.
        """
        return None

    def layout(self,pycell=None,data=None):
        self.ignoreBoundaryRouting = False
        self.log.info(f"Assembling layout....")

        self.hierarchy()

        self._runMethod(pycell,data,"beforePlace")
        #- Place cell
        self.log.info(f"place()")
        self.place()

        self._runMethod(pycell,data,"afterPlace")

        # Route internal (dummy) routes immediately so later routes can use their geometry
        for r in list(self.routes):
            if getattr(r, 'debug_internal', False):
                r.route()
                r._pre_routed = True

        #- STACKS ROUTE THEMSELVES FIRST, and the system asks them --
        #- the design should not have to wire this up in its own
        #- beforeRoute. Innermost first is the whole point of the
        #- hierarchy: a stack's internal nets are settled against a
        #- handful of instances before the parent commits a single
        #- track to crossing the cell.
        #-
        #- HERE, and not in afterPaint where it used to sit. A pycell
        #- called after paint can add all the Routes it likes; route()
        #- has already run and nothing will ever draw them. That is what
        #- made the first stack pycell look like it worked -- it logged
        #- a success and left every net it touched open.
        self._runStackPycells()

        self._runMethod(pycell,data,"beforeRoute")

        self.log.info(f"route()")
        self.route()

        self._runMethod(pycell,data,"afterRoute")

        self._runMethod(pycell,data,"beforePaint")

        self.log.info(f"paint()")

        self._runMethod(pycell,data,"afterPaint")


        self._runMethod(pycell,data,"beforePorts")
        self.log.info(f"addAllPorts()")
        self.addAllPorts()
        self._runMethod(pycell,data,"afterPorts")
