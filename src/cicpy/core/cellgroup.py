#!/usr/bin/env python3

"""Group classes used during placement and routing.

Hierarchy:

    LayoutCell
        ↑
    CellGroup           — base for named placement groups (this file)
        ↑
    StackGroup          — vertical column-major array of instances

    Cell
        ↑
    RouteBundle         — container of locally-scoped routes + ports
                          produced inside a StackGroup. Not a placement
                          group: holds geometry only, references members.

`RouteBundle` is what older revisions called `ParallelGroup`. It is a
plain `Cell` (not a `CellGroup`) because it never owns instances and is
never abutted; it lives inside the StackGroup that produced it and
exposes a subset of its routed nets as Ports.
"""

import re

from .cell import Cell
from .layoutcell import LayoutCell
from .rules import Rules
from .port import Port
from .rect import Rect


class _PhysicalInst:
    def __init__(self, name, subckt_name):
        self.name = name
        self.subcktName = subckt_name


class RouteBundle(Cell):
    """Locally-scoped routes + ports bundled inside a StackGroup.

    Members are referenced by identity. The bundle owns route rects and
    exposes ports via `addGroupPort`.
    """

    def __init__(self, layout, name, members=None):
        super().__init__(name)
        self.layout = layout
        self.members = list(members or [])
        self.route_rects = []
        self.group_ports = {}

    # Backward-compat alias: bundles used to be called ParallelGroup
    # and its members were exposed as ``instances``.
    @property
    def instances(self):
        return self.members

    def _members(self):
        return self.members + self.route_rects + list(self.group_ports.values())

    def calcBoundingRect(self):
        members = self._members()
        if not members:
            return super().calcBoundingRect()
        return Cell.calcBoundingRectFromList(members, False)

    def translate(self, dx, dy):
        for obj in self.route_rects + list(self.group_ports.values()):
            obj.translate(dx, dy)
        self.updateBoundingRect()
        self.emit_updated()

    def addRouteRect(self, rect):
        self.route_rects.append(rect)
        self.add(rect)
        self.updateBoundingRect()
        return rect

    def addGroupPort(self, net, rect, edge, terminal=None):
        port = Port(net, routeLayer=rect.layer, rect=rect)
        port.spicePort = False
        port.side = edge
        port.terminalName = terminal or ""
        self.group_ports[net] = port
        self.add(port)
        self.updateBoundingRect()
        return port

    def representativeAccessRects(self, net, accessLayer=None, terminalFilter="nonbulk"):
        port = self.group_ports.get(net)
        if port is None:
            return []
        if not _terminal_allowed(getattr(port, "terminalName", ""), terminalFilter):
            return []
        rect = port.get(accessLayer)
        if accessLayer and rect is not None and getattr(rect, "layer", "") != accessLayer:
            return []
        return [rect] if rect is not None else []

    def toJson(self):
        return {
            "class": "RouteBundle",
            "name": self.name,
            "bbox": _bbox_json(self),
            "members": [getattr(m, "instanceName", "") for m in self.members],
            "routes": [
                {
                    "layer": getattr(r, "layer", ""),
                    "net": getattr(r, "net", ""),
                    "x1": r.x1, "y1": r.y1, "x2": r.x2, "y2": r.y2,
                }
                for r in self.route_rects
            ],
            "ports": _ports_json(self.group_ports.values()),
        }


# Backward-compat: older code referenced this class as ParallelGroup.
ParallelGroup = RouteBundle


def _rect_json(obj):
    if obj is None:
        return None
    return {
        "x1": obj.x1,
        "y1": obj.y1,
        "x2": obj.x2,
        "y2": obj.y2,
        "layer": getattr(obj, "layer", ""),
        "net": getattr(obj, "net", ""),
    }


def _bbox_json(obj):
    if obj is None:
        return None
    try:
        obj.updateBoundingRect()
    except Exception:
        pass
    return _rect_json(obj)


def _port_json(port):
    if port is None:
        return None
    rect = port.get(getattr(port, "routeLayer", None)) if hasattr(port, "get") else port
    data = _rect_json(rect)
    if data is None:
        return None
    data["name"] = getattr(port, "name", "")
    data["routeLayer"] = getattr(port, "routeLayer", data.get("layer", ""))
    data["side"] = getattr(port, "side", "")
    data["spicePort"] = getattr(port, "spicePort", False)
    terminal = getattr(port, "terminalName", "")
    if terminal:
        data["terminal"] = terminal
    return data


def _ports_json(ports):
    out = []
    for port in ports:
        data = _port_json(port)
        if data is not None:
            out.append(data)
    return out


def _dedupe_ports(ports):
    out = []
    seen = set()
    for port in ports:
        key = (
            getattr(port, "name", ""),
            getattr(port, "routeLayer", ""),
            getattr(port, "x1", None),
            getattr(port, "y1", None),
            getattr(port, "x2", None),
            getattr(port, "y2", None),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(port)
    return out


def _terminal_filter_from_options(options=""):
    opts = options or ""
    match = re.search(r"(?:terminal|terminals|term)\s*=\s*([A-Za-z,]+)", opts, re.I)
    if match:
        return {term.strip().upper() for term in match.group(1).split(",") if term.strip()}
    if re.search(r"(?:onBulk|bulk)(,|\s+|$)", opts, re.I):
        return {"B"}
    if re.search(r"allTerminals(,|\s+|$)", opts, re.I):
        return None
    return "nonbulk"


def _terminal_allowed(terminal_name, terminal_filter):
    if terminal_filter is None:
        return True
    terminal = (terminal_name or "").upper()
    if terminal_filter == "nonbulk":
        return terminal != "B"
    return terminal in terminal_filter


class CellGroup(LayoutCell):
    """Base class for named placement groups.

    Inherits LayoutCell so groups have their own port/connectivity
    context and serialize into JSON via `toJson`. A CellGroup contains
    StackGroups (or other CellGroups) and exposes group-scoped routing
    helpers that delegate to the parent layout's routing engine but
    constrain matching to the group's member instances.
    """

    def __init__(self, layout, name=""):
        super().__init__()
        self.name = name
        self.layout = layout
        self.boundary_ports = {}

    @property
    def stacks(self):
        return [c for c in self.children if isinstance(c, StackGroup)]

    # ------------------------------------------------------------------
    # Group-scoped routing
    # ------------------------------------------------------------------
    def _route_instances(self):
        data = []
        for stack in self.stacks:
            data.extend(stack._route_instances())
        return data

    def instanceRegex(self):
        names = [re.escape(inst.instanceName) for inst in self._route_instances()]
        if not names:
            return ""
        return "^(" + "|".join(names) + ")$"

    def addConnectivityRoute(self, layer, regex, routeType, options="", cuts=1, excludeInstances=""):
        include = self.instanceRegex()
        self.layout.addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances, include)
        return self

    def addOrthogonalConnectivityRoute(self, verticalLayer, horizontalLayer, regex, options="", cuts=1, excludeInstances=""):
        include = self.instanceRegex()
        self.layout.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, include)
        return self

    def representativeAccessRects(self, net, accessLayer, anymetal=False, terminalFilter="nonbulk"):
        rects = []
        for stack in self.stacks:
            rects.extend(stack.representativeAccessRects(net, accessLayer, anymetal=anymetal, terminalFilter=terminalFilter))
        return self.layout.collapseRepresentativeRects(net, rects)

    def memberNames(self):
        return {getattr(inst, "instanceName", "") for inst in self._route_instances()}

    def _boundary_nets(self, forceNets=None, hideNets=None, excludeNets=""):
        force = set(forceNets or [])
        hide = set(hideNets or [])
        members = self.memberNames()
        boundary = set()
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is None:
            return sorted(force - hide)
        for net, node in graph.items():
            if excludeNets and re.search(excludeNets, net):
                continue
            if net in hide:
                continue
            inside = False
            outside = net in getattr(self.layout, "ports", {})
            for port in getattr(node, "ports", []):
                inst = getattr(port, "parent", None)
                if inst is None or not inst.isInstance():
                    continue
                instance_name = getattr(inst, "instanceName", "")
                if instance_name in members:
                    inside = True
                else:
                    outside = True
            if (inside and outside) or net in force:
                boundary.add(net)
        boundary.update(force - hide)
        return sorted(boundary)

    def _select_boundary_rect(self, rects, options=""):
        opts = options or ""
        if re.search(r"onTopLeft(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (-r.y2, r.x1, r.y1))[0]
        if re.search(r"onTopRight(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (-r.y2, -r.x2, r.y1))[0]
        if re.search(r"onBottomLeft(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (r.y1, r.x1, r.x2))[0]
        if re.search(r"onBottomRight(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (r.y1, -r.x2, r.x1))[0]
        if re.search(r"onLeftTop(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (r.x1, -r.y2, r.y1))[0]
        if re.search(r"onLeftBottom(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (r.x1, r.y1, r.y2))[0]
        if re.search(r"onRightTop(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (-r.x2, -r.y2, r.y1))[0]
        if re.search(r"onRightBottom(,|\s+|$)", opts, re.I):
            return sorted(rects, key=lambda r: (-r.x2, r.y1, r.y2))[0]
        self.updateBoundingRect()
        target_x = 0.5 * (self.left() + self.right()) if hasattr(self, "left") else 0
        target_y = 0.5 * (self.bottom() + self.top()) if hasattr(self, "bottom") else 0
        return min(rects, key=lambda r: (abs(r.centerY() - target_y), abs(r.centerX() - target_x), r.x1, r.y1))

    def _make_boundary_port(self, net, layer, rects, options=""):
        if not rects:
            return None
        source = self._select_boundary_rect(rects, options=options)
        # Boundary port lives on the source rect's actual layer; the route
        # engine adds the cuts to bridge to the requested layer.
        port_layer = getattr(source, "layer", "") or layer
        rect = source.getCopy(port_layer)
        rect.net = net
        port = Port(net, routeLayer=port_layer, rect=rect)
        port.spicePort = False
        port.side = "boundary"
        return port

    def exportBoundaryPorts(self, layer="M2", excludeNets="", forceNets=None, hideNets=None, options=""):
        ports = []
        terminal_filter = _terminal_filter_from_options(options)
        for net in self._boundary_nets(forceNets=forceNets, hideNets=hideNets, excludeNets=excludeNets):
            rects = self.representativeAccessRects(net, layer, terminalFilter=terminal_filter)
            port = self._make_boundary_port(net, layer, rects, options=options)
            if port is None:
                continue
            self.boundary_ports[(net, layer, options or "")] = port
            ports.append(port)
        return _dedupe_ports(ports)

    def checkInternalConnectivity(self, warnOnly=True):
        boundary = set(self._boundary_nets())
        members = self.memberNames()
        internal = []
        routed = set()
        if hasattr(self, "routedNets"):
            routed.update(self.routedNets())
        for stack in self.stacks:
            routed.update(stack.routedNets())
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is not None:
            for net, node in graph.items():
                if net in boundary:
                    continue
                count = 0
                for port in getattr(node, "ports", []):
                    inst = getattr(port, "parent", None)
                    if inst is not None and inst.isInstance() and getattr(inst, "instanceName", "") in members:
                        count += 1
                if count > 1:
                    internal.append(net)
        opens = sorted(net for net in internal if net not in routed)
        if warnOnly:
            for net in opens:
                self.log.warning(f"Internal group net may be incomplete: group={self.name} net={net}")
        return {
            "boundary_nets": sorted(boundary),
            "internal_nets": sorted(internal),
            "opens": opens,
        }

    # ------------------------------------------------------------------
    # Stack creation
    # ------------------------------------------------------------------
    def addStack(self, name, instances, preserveOrder=False):
        stack = StackGroup(self.layout, name)
        stack.preserve_order = preserveOrder
        stack.addInstances(instances)
        self.add(stack)
        self.updateBoundingRect()
        return stack

    def addStackByGroup(self, groupName, name=None, fillGroup=None):
        instances = self.layout.getSortedInstancesByGroupName(groupName)
        if fillGroup is not None:
            instances.extend(self.layout.getSortedInstancesByGroupName(fillGroup))
        return self.addStack(name or groupName, instances, preserveOrder=True)

    def addParallelStack(self, name, instances, preserveOrder=False):
        return self.addStack(name, instances, preserveOrder=preserveOrder)

    def addParallelStackByGroup(self, groupName, name=None, fillGroup=None):
        return self.addStackByGroup(groupName, name=name, fillGroup=fillGroup)

    def addTransistorStackByGroup(self, groupName, name=None, fillGroup=None, layer="M2", terminals=("D", "G", "S"), edge="top", edges=None, excludeInstances="", excludeNets="", minRects=None, sameTerminal=True, routeDiodes=True, diodeLayer="M1"):
        stack = self.addStackByGroup(groupName, name=name, fillGroup=fillGroup)
        stack.kind = "transistorStack"
        stack.stack().addTaps()
        if routeDiodes:
            stack.routeDiodeConnected(layer=diodeLayer, excludeInstances=excludeInstances)
        stack.routeParallel(
            layer=layer,
            terminals=terminals,
            edge=edge,
            edges=edges,
            excludeInstances=excludeInstances,
            excludeNets=excludeNets,
            minRects=minRects,
            sameTerminal=sameTerminal,
        )
        return stack

    def transistorStack(self, groupName, name=None, fillGroup=None, **route_kwargs):
        return self.addTransistorStackByGroup(groupName, name=name, fillGroup=fillGroup, **route_kwargs)

    def addCurrentMirrorStackByGroup(self, groupName, name=None, fillGroup=None, layer="M2", terminals=("G", "S"), edge="top", edges=None, excludeInstances="^xfill_", excludeNets="", minRects=2, sameTerminal=True, routeDiodes=True, diodeLayer="M1"):
        stack = self.addStackByGroup(groupName, name=name, fillGroup=fillGroup)
        stack.kind = "mirrorStack"
        stack.stack().addTaps()
        if routeDiodes:
            stack.routeDiodeConnected(layer=diodeLayer, excludeInstances=excludeInstances)
        stack.routeMirror(
            layer=layer,
            terminals=terminals,
            edge=edge,
            edges=edges,
            excludeInstances=excludeInstances,
            excludeNets=excludeNets,
            minRects=minRects,
            sameTerminal=sameTerminal,
        )
        return stack

    def currentMirrorStack(self, groupName, name=None, fillGroup=None, **route_kwargs):
        return self.addCurrentMirrorStackByGroup(groupName, name=name, fillGroup=fillGroup, **route_kwargs)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def calcBoundingRect(self):
        if not self.stacks:
            return super().calcBoundingRect()
        active = [stack for stack in self.stacks if stack.instances]
        if not active:
            return super().calcBoundingRect()
        return Cell.calcBoundingRectFromList(active, False)

    def left(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.x1

    def right(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.x2

    def bottom(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.y1

    def top(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.y2

    def abutTop(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - self.left())
        dy = int(other.top() + space - self.bottom())
        self.translate(dx, dy)
        return self

    def abutBottom(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - self.left())
        dy = int(other.bottom() - space - self.top())
        self.translate(dx, dy)
        return self

    def abutLeft(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - space - self.right())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def abutRight(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.right() + space - self.left())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def moveAbove(self, other, ygap=0):
        return self.abutTop(other, ygap)

    def moveBelow(self, other, ygap=0):
        return self.abutBottom(other, ygap)

    def fillDummyTransistors(self, direction="top"):
        if not self.stacks:
            return self
        target_height = max(stack.height() for stack in self.stacks)
        for stack in self.stacks:
            stack.fillDummyTransistors(target_height, direction=direction)
        self.updateBoundingRect()
        return self

    def routeDummyDevices(self):
        for stack in self.stacks:
            stack.routeDummyDevices()
        self.updateBoundingRect()
        return self

    def exportedPorts(self):
        return self.exportBoundaryPorts()

    # ------------------------------------------------------------------
    # JSON output
    # ------------------------------------------------------------------
    def toJson(self):
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "bbox": _bbox_json(self),
            "ports": _ports_json(self.exportedPorts()),
            "stacks": [s.toJson() for s in self.stacks],
        }


class StackGroup(CellGroup):
    """Vertical column-major array of instances.

    Owns stacking, taps, dummy fill and the route bundles produced by
    `routeParallel` / `routeMirror`. Member instances are moved under
    the stack so placement tree walkers visit them once.
    """

    def __init__(self, layout, name):
        super().__init__(layout, name)
        self.instances = []
        self.tap_instances = []
        self.dummy_routes = []
        self.direct_routes = []
        self.diode_routes = []
        self.route_bundles = []
        self.preserve_order = False
        self.kind = "stack"

    # Backward-compat alias for code that still reads `parallel_groups`.
    @property
    def parallel_groups(self):
        return self.route_bundles

    def _members(self):
        members = []
        seen = set()
        for obj in (
            self.instances
            + self.tap_instances
            + self.dummy_routes
            + self.direct_routes
            + self.route_bundles
        ):
            if obj is None:
                continue
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            members.append(obj)
        return members

    def _route_instances(self):
        return [inst for inst in self.instances if inst is not None and getattr(inst, "instanceName", "")]

    def _route_instances_excluding(self, excludeInstances=""):
        instances = []
        for inst in self._route_instances():
            instance_name = getattr(inst, "instanceName", "")
            if excludeInstances and (
                re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(inst, "name", ""))
            ):
                continue
            instances.append(inst)
        return instances

    def instanceRegex(self):
        names = [re.escape(inst.instanceName) for inst in self._route_instances()]
        if not names:
            return ""
        return "^(" + "|".join(names) + ")$"

    def addConnectivityRoute(self, layer, regex, routeType, options="", cuts=1, excludeInstances=""):
        include = self.instanceRegex()
        self.layout.addConnectivityRoute(layer, regex, routeType, options, cuts, excludeInstances, include)
        return self

    def addOrthogonalConnectivityRoute(self, verticalLayer, horizontalLayer, regex, options="", cuts=1, excludeInstances=""):
        include = self.instanceRegex()
        self.layout.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, include)
        return self

    def representativeAccessRects(self, net, accessLayer, anymetal=False, terminalFilter="nonbulk"):
        rects = []
        for bundle in self.route_bundles:
            rects.extend(bundle.representativeAccessRects(net, accessLayer, terminalFilter=terminalFilter))
        if rects:
            return self.layout.collapseRepresentativeRects(net, rects)
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is None or net not in graph:
            return []
        node = graph.get(net)
        if node is None:
            return []
        member_names = {getattr(i, "instanceName", "") for i in self._route_instances()}
        rects = []
        for port in getattr(node, "ports", []):
            inst = getattr(port, "parent", None)
            if inst is None or not inst.isInstance():
                continue
            instance_name = getattr(inst, "instanceName", "")
            if instance_name not in member_names:
                continue
            terminal_name = getattr(port, "childName", "")
            if not _terminal_allowed(terminal_name, terminalFilter):
                continue
            rect = port.get(accessLayer) if hasattr(port, "get") else None
            if rect is None:
                continue
            rects.append(rect)
        rects = self.layout.collapseRepresentativeRects(net, rects)
        if not rects:
            return []
        target_y = 0.5 * (self.bottom() + self.top())
        chosen = min(rects, key=lambda r: (abs(r.centerY() - target_y), abs(r.centerX() - self.left()), r.x1, r.y1))
        return [chosen]

    def routedNets(self):
        nets = set()
        for bundle in self.route_bundles:
            for rect in getattr(bundle, "route_rects", []):
                net = getattr(rect, "net", "")
                if net:
                    nets.add(net)
        for rect in self.direct_routes + self.diode_routes:
            net = getattr(rect, "net", "")
            if net:
                nets.add(net)
        for route in self.dummy_routes:
            net = getattr(route, "net", "")
            if net:
                nets.add(net)
        return nets

    def _bus_group_name(self, instance_name):
        if not re.search(r"<[^>]+>$", instance_name or ""):
            return ""
        return re.sub(r"<[^>]+>$", "", instance_name)

    def _parallel_instance_groups(self, excludeInstances=""):
        groups = {}
        for inst in self._route_instances():
            instance_name = getattr(inst, "instanceName", "")
            if excludeInstances and (
                re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(inst, "name", ""))
            ):
                continue
            group_name = self._bus_group_name(instance_name)
            if not group_name:
                continue
            groups.setdefault(group_name, []).append(inst)
        out = []
        for name, instances in groups.items():
            if len(instances) < 2:
                continue
            instances = sorted(instances, key=lambda inst: (inst.y1, inst.x1, getattr(inst, "instanceName", "")))
            out.append(RouteBundle(self.layout, f"{self.name}_{name}", instances))
        return out

    def _ports_by_net(self, instances, terminals=None, layer="M2", excludeInstances="", excludeNets="", sameTerminal=True):
        """Resolve nodeGraph ports for ``instances`` into a per-net rect list
        on ``layer``. Pin geometry is read from ``port.get(layer)``; ports
        whose ``routeLayer`` doesn't match ``layer`` are skipped — those
        nets simply won't be tied at that layer (caller's responsibility to
        choose a layer the device actually exposes).
        """
        terminal_set = set(terminals or [])
        member_names = {getattr(i, "instanceName", "") for i in instances}
        grouped = {}
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is None:
            return grouped
        for net, node in graph.items():
            if excludeNets and re.search(excludeNets, net):
                continue
            terminal_rects = {}
            seen = {}
            for port in getattr(node, "ports", []):
                inst = getattr(port, "parent", None)
                if inst is None or not inst.isInstance():
                    continue
                instance_name = getattr(inst, "instanceName", "")
                if instance_name not in member_names:
                    continue
                if excludeInstances and (
                    re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(inst, "name", ""))
                ):
                    continue
                terminal_name = getattr(port, "childName", "")
                if terminal_set and terminal_name not in terminal_set:
                    continue
                rect = port.get(layer) if hasattr(port, "get") else None
                if rect is None:
                    continue
                if getattr(rect, "layer", "") != layer:
                    continue
                key_name = terminal_name if sameTerminal else ""
                terminal_rects.setdefault(key_name, [])
                seen.setdefault(key_name, set())
                key = (rect.layer, rect.x1, rect.y1, rect.x2, rect.y2)
                if key in seen[key_name]:
                    continue
                seen[key_name].add(key)
                terminal_rects[key_name].append(rect)
            terminal_rects = {term: rects for term, rects in terminal_rects.items() if rects}
            if not terminal_rects:
                continue
            term, rects = max(terminal_rects.items(), key=lambda item: (len(item[1]), item[0]))
            grouped[net] = (term, rects)
        return grouped

    def _vertical_parallel_rect(self, layer, rects, align="full", step=0):
        """A rail down a column of parallel devices, over one terminal.

        ``align`` picks which part of the pin the rail sits on, and on a
        library whose pins overlap in x that is the whole game. A
        library may lay its source rail over one span of its pattern
        columns and the drain run over another that overlaps it, so a
        rail taking the full pin width for each shorts them the moment
        both
        are asked for. Taking the *left* edge for one and the *right*
        edge for the other keeps each on the part of its pin the other
        does not have, and both stay on M1.

        Which edge belongs to which terminal is the caller's to say,
        because it is a property of the library, not of the net.
        """
        if not rects:
            return None
        source = sorted(rects, key=lambda r: (r.y1, r.x1))[0]
        y1 = min(r.y1 for r in rects)
        y2 = max(r.y2 for r in rects)

        if align in ("left", "right"):
            #- one routing width at the edge of the span every pin in
            #- the column shares, not the pin width: the point of the
            #- edge is to leave the rest of the pin to the terminal that
            #- overlaps it.
            #-
            #- ``step`` walks inward from that edge by a routing pitch at
            #- a time. A column whose devices carry several nets on one
            #- terminal -- a series ladder, a bias stack -- cannot give
            #- them all the edge, and railing them all at the same x is
            #- how they short. Each net takes the next lane in.
            rules = Rules.getInstance()
            width = rules.get(layer, "width")
            pitch = width + rules.get(layer, "space")
            lo = max(r.x1 for r in rects)
            hi = min(r.x2 for r in rects)
            if hi - lo < width + step * pitch:
                return None
            x1 = lo + step * pitch if align == "left" else hi - width - step * pitch
        else:
            x1, width = source.x1, source.width()

        rect = Rect(layer, x1, y1, width, y2 - y1)
        rect.net = getattr(source, "net", "")
        return rect

    def _railsClash(self, a, b):
        """Two column rails that would touch, spacing included."""
        space = Rules.getInstance().get(a.layer, "space")
        return not (a.x2 + space <= b.x1 or b.x2 + space <= a.x1
                    or a.y2 + space <= b.y1 or b.y2 + space <= a.y1)

    def _terminal_net(self, inst, terminal):
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is None:
            return None
        for net, node in graph.items():
            for port in getattr(node, "ports", []):
                if getattr(port, "parent", None) is not inst:
                    continue
                if getattr(port, "childName", "") == terminal:
                    return net
        return None

    def _terminal_rects(self, inst, terminal, layer):
        """The geometry of one *terminal* of one instance, on ``layer``.

        Keyed by terminal, not by net: two terminals of a diode
        connected device share a net and the net keyed lookups cannot
        separate them.
        """
        graph = getattr(self.layout, "nodeGraph", None)
        if graph is None:
            return []
        out = []
        for node in graph.values():
            for port in getattr(node, "ports", []):
                if getattr(port, "parent", None) is not inst:
                    continue
                if getattr(port, "childName", "") != terminal:
                    continue
                rect = port.get(layer) if hasattr(port, "get") else None
                if rect is not None:
                    #- a copy: Route stretches the rectangles it is given,
                    #- and these are the device's own pins
                    out.append(rect.getCopy())
        return out

    def _diodeStrapRects(self, d, g, layer):
        """Metal joining two pin rectangles of one device, on one layer.

        Not a route. A route aligns to pin edges and reasons about
        tracks, which is the right thing when the wire has somewhere to
        go; a diode tie has nowhere to go. It has to land *on* the two
        rectangles and nothing more, so it is drawn as one or two blocks
        that overlap them. Landing anywhere inside the pin counts.
        """
        w = Rules.getInstance().get(layer, "width")

        ox = min(d.x2, g.x2) - max(d.x1, g.x1)
        oy = min(d.y2, g.y2) - max(d.y1, g.y1)
        if ox > 0 and oy > 0:
            #- already touching, the library tied them itself
            return []

        def widen(a, b):
            if b - a >= w:
                return a, b
            c = (a + b) // 2
            return c - w // 2, c - w // 2 + w

        if ox > 0:
            x1, x2 = widen(max(d.x1, g.x1), min(d.x2, g.x2))
            y1, y2 = min(d.y1, g.y1), max(d.y2, g.y2)
            return [Rect(layer, x1, y1, x2 - x1, y2 - y1)]
        if oy > 0:
            y1, y2 = widen(max(d.y1, g.y1), min(d.y2, g.y2))
            x1, x2 = min(d.x1, g.x1), max(d.x2, g.x2)
            return [Rect(layer, x1, y1, x2 - x1, y2 - y1)]

        #- diagonal, which is where a compact library tends to put
        #- them: G a tab above and to one side of the wide D bar. A block in the gate's own
        #- column reaching down into the drain's band, and a short bar
        #- along that band back into the drain
        gx1, gx2 = widen(g.x1, g.x2)
        dy1, dy2 = widen(d.y1, d.y2)
        vy1, vy2 = min(dy1, g.y1), max(dy2, g.y2)
        if gx1 >= d.x2:
            hx1, hx2 = max(d.x1, d.x2 - w), gx2
        else:
            hx1, hx2 = gx1, min(d.x2, d.x1 + w)
        return [
            Rect(layer, hx1, dy1, hx2 - hx1, dy2 - dy1),
            Rect(layer, gx1, vy1, gx2 - gx1, vy2 - vy1),
        ]

    def _edge_port_rect(self, layer, route_rect, edge, port_height):
        if route_rect is None:
            return None
        height = min(port_height, route_rect.height())
        width = route_rect.width()
        if edge == "top":
            return Rect(layer, route_rect.x1, route_rect.y2 - height, width, height)
        if edge == "bottom":
            return Rect(layer, route_rect.x1, route_rect.y1, width, height)
        if edge == "left":
            return Rect(layer, route_rect.x1, route_rect.y1, width, height)
        if edge == "right":
            return Rect(layer, route_rect.x2 - width, route_rect.y1, width, height)
        if edge in ("middle", "center"):
            y = int(route_rect.centerY() - height / 2)
            return Rect(layer, route_rect.x1, y, width, height)
        raise ValueError(f"Unsupported parallel port edge '{edge}'")

    def routeParallel(self, layer="M2", terminals=("D", "G", "S"), edge="top", edges=None, excludeInstances="", excludeNets="", minRects=None, sameTerminal=True):
        """Join repeated device terminals inside the stack and expose one bundle port per net."""
        for bundle in self._parallel_instance_groups(excludeInstances=excludeInstances):
            nets = self._ports_by_net(bundle.members, terminals=terminals, layer=layer, excludeInstances=excludeInstances, excludeNets=excludeNets, sameTerminal=sameTerminal)
            required_rects = minRects if minRects is not None else len(bundle.members)
            required_rects = max(2, required_rects)
            for net, (terminal_name, rects) in nets.items():
                if len(rects) < required_rects:
                    continue
                route_rect = self._vertical_parallel_rect(layer, rects)
                if route_rect is None:
                    continue
                route_rect.net = net
                bundle.addRouteRect(route_rect)

                port_edge = edges.get(net, edge) if edges else edge
                port_rect = self._edge_port_rect(layer, route_rect, port_edge, rects[0].height())
                if port_rect is None:
                    continue
                port_rect.net = net
                bundle.addGroupPort(net, port_rect, port_edge, terminal=terminal_name)

            if bundle.route_rects:
                self.route_bundles.append(bundle)
                self.add(bundle)
        self.updateBoundingRect()
        return self

    def routeMirror(self, layer="M2", terminals=("G", "S"), edge="top", edges=None, excludeInstances="^xfill_", excludeNets="", minRects=2, sameTerminal=True, align="full"):
        """Route common mirror terminals across the whole stack as one bundle.

        ``align`` is passed to the rail: ``"full"`` takes the pin's own
        width, ``"left"`` and ``"right"`` take one routing width at that
        edge of the span the column's pins share. Use an edge when two
        terminals of the library overlap in x, which is what stops both
        from being railed on the same layer.
        """
        instances = self._route_instances_excluding(excludeInstances=excludeInstances)
        if len(instances) < 2:
            return self
        bundle = RouteBundle(self.layout, f"{self.name}_mirror", sorted(instances, key=lambda inst: (inst.y1, inst.x1, getattr(inst, "instanceName", ""))))
        nets = self._ports_by_net(bundle.members, terminals=terminals, layer=layer, excludeInstances=excludeInstances, excludeNets=excludeNets, sameTerminal=sameTerminal)
        required_rects = minRects if minRects is not None else 2
        required_rects = max(2, required_rects)
        #- rails already placed in this column, so the next net can be
        #- given a lane that clears them instead of landing on top. The
        #- longest span goes first: it has the least room to move and
        #- the most to lose by being pushed inward
        placed = []
        ordered = sorted(
            nets.items(),
            key=lambda kv: -(max(r.y2 for r in kv[1][1]) - min(r.y1 for r in kv[1][1])))
        for net, (terminal_name, rects) in ordered:
            if len(rects) < required_rects:
                continue
            #- every pin of this terminal that is NOT on this net. A rail
            #- down the column crosses whatever shares the column, and on
            #- this library the pins of one terminal all sit at the same
            #- x, so a foreign pin inside the rail's span cannot be
            #- stepped around -- it can only be refused. A column with
            #- two nets on one terminal is not a mirror and has to be
            #- routed a layer up
            foreign = [r for other, (_, rs) in nets.items() if other != net
                       for r in rs]
            route_rect = None
            for step in range(0, 16):
                cand = self._vertical_parallel_rect(layer, rects, align=align, step=step)
                if cand is None:
                    break
                if any(self._railsClash(cand, other) for other in placed):
                    continue
                if any(self._railsClash(cand, other) for other in foreign):
                    break
                route_rect = cand
                break
            if route_rect is None:
                self.log.info(
                    f"routeMirror: no {align} rail for {net} in {self.name}, "
                    f"the column carries other nets on {terminal_name}")
                continue
            placed.append(route_rect)
            route_rect.net = net
            bundle.addRouteRect(route_rect)

            port_edge = edges.get(net, edge) if edges else ("middle" if terminal_name == "S" else edge)
            port_rect = self._edge_port_rect(layer, route_rect, port_edge, rects[0].height())
            if port_rect is None:
                continue
            port_rect.net = net
            bundle.addGroupPort(net, port_rect, port_edge, terminal=terminal_name)

        if bundle.route_rects:
            self.route_bundles.append(bundle)
            self.add(bundle)
        self.updateBoundingRect()
        return self

    def routeDiodeConnected(self, layer="M1", drain="D", gate="G", excludeInstances=""):
        """Tie drain to gate on every diode-connected device in the stack.

        A diode tie is the shortest wire in a layout: two pins of one
        transistor, a couple of microns apart, inside the device's own
        footprint. It belongs on the pin layer. Spending a routing layer
        on it costs a via pair and, worse, a track through the column
        that a net with somewhere to go could have used.

        It is drawn as metal, not as a route. A route aligns to pin
        edges; a tie only has to land on the two rectangles, and asking
        for an edge alignment it does not need is what pushed the wire
        outside the device and moved the cell origin with it.

        The pin rectangles come from the node graph, not from the
        ``instance:terminal`` path grammar. On a cell built from a
        netlist an instance's ports are keyed by *net*, and a diode
        connected device has one net on two terminals, so the two
        collapse to a single entry and the path form finds nothing —
        which is why this used to report ``start=0 stop=0`` on every
        device it was asked about. The graph keeps the terminal name,
        so it can still tell drain from gate.

        The metal is tracked on the stack as ``self.diode_routes`` and
        parented under it so JSON and bounding box walks see it.
        """
        bundle = RouteBundle(self.layout, f"{self.name}_diode",
                             self._route_instances_excluding(excludeInstances="^xfill_"))
        for inst in self._route_instances():
            instance_name = getattr(inst, "instanceName", "")
            if not instance_name:
                continue
            if excludeInstances and (
                re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(inst, "name", ""))
            ):
                continue

            drain_net = self._terminal_net(inst, drain)
            gate_net = self._terminal_net(inst, gate)
            if not drain_net or drain_net != gate_net:
                continue

            start = self._terminal_rects(inst, drain, layer)
            stop = self._terminal_rects(inst, gate, layer)
            if not start or not stop:
                self.log.error(
                    f"routeDiodeConnected: {instance_name} has no {layer} "
                    f"geometry for {drain if not start else gate}")
                continue

            rects = self._diodeStrapRects(start[0], stop[0], layer)
            for rect in rects:
                rect.net = drain_net
                bundle.addRouteRect(rect)
                self.diode_routes.append(rect)
        if bundle.route_rects:
            self.route_bundles.append(bundle)
            self.add(bundle)
        self.updateBoundingRect()
        return self

    def translate(self, dx, dy):
        for obj in self._members():
            obj.translate(dx, dy)
        self.updateBoundingRect()
        self.emit_updated()

    def addInstance(self, inst):
        if inst not in self.instances:
            self.instances.append(inst)
        if inst not in self.children:
            self.layout.detachPlacementChild(inst, keepParent=self)
        self.add(inst)
        self.updateBoundingRect()
        return inst

    def addInstances(self, instances):
        for inst in instances:
            self.addInstance(inst)
        self.updateBoundingRect()
        return self

    def orderByTerminalNet(self, terminal="D"):
        """Reorder the column so each net's pins on ``terminal`` are adjacent.

        A rail down a column crosses every pin it passes, so a net whose
        pins are interleaved with another's cannot have one. Placement
        decides that, not routing: a load column measured in the wild
        came out A A A A **B** A, and moving the one odd device to the
        end of the column is the difference between a rail and a trip up
        a layer and back for five pins.

        Grouping is stable, so a net keeps the internal order the
        placement gave it and the nets keep the order of their first
        appearance. Devices with no net on that terminal go last.

        This buys one terminal, not all of them, and the caller chooses
        which: ordering by drain scatters the gates. Nothing electrical
        rides on it — the netlist is what it is and reordering a column
        cannot change connectivity — but two kinds of stack still must
        not be touched: a series chain, where the order is what makes
        each link a neighbour, and a matched pair, where it is the
        matching. Neither is detectable from here, so this is opt in and
        calling it overrides ``preserve_order``: the call *is* the
        statement of intent.
        """
        order, seen = [], {}
        for inst in self.instances:
            net = self._terminal_net(inst, terminal) or "￿"
            seen.setdefault(net, []).append(inst)
        for net in seen:
            order.extend(seen[net])
        if [id(i) for i in order] != [id(i) for i in self.instances]:
            self.log.info(
                f"orderByTerminalNet: {self.name} regrouped on {terminal} into "
                + ", ".join(f"{n if n != chr(0xffff) else '(none)'}x{len(v)}"
                            for n, v in seen.items()))
        self.instances = order
        #- the packing has to be redone from the new order, and sort()
        #- would undo it, so hold the order while stack() runs
        was = self.preserve_order
        self.preserve_order = True
        self.stack()
        self.preserve_order = was
        return self

    def sort(self):
        if self.preserve_order:
            self.updateBoundingRect()
            return self
        self.instances = sorted(self.instances, key=lambda inst: (inst.y1, inst.x1, inst.instanceName))
        self.updateBoundingRect()
        return self

    def calcBoundingRect(self):
        members = self._members()
        if not members:
            return Cell.calcBoundingRect(self)
        return Cell.calcBoundingRectFromList(members, False)

    def height(self):
        if not self.instances:
            return 0
        self.sort()
        return self.instances[-1].y2 - self.instances[0].y1

    def width(self):
        if not self.instances:
            return 0
        self.sort()
        return max(inst.width() for inst in self.instances)

    def left(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.x1

    def bottom(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.y1

    def top(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.y2

    def stack(self, x=None, y=None, ygap=0):
        if not self.instances:
            return self
        self.sort()
        if x is None:
            x = self.left()
        if y is None:
            y = self.bottom()
        ypos = int(y)
        for inst in self.instances:
            inst.moveTo(int(x), ypos)
            ypos = int(inst.y2 + ygap)
        self.updateBoundingRect()
        return self

    def right(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.x2

    def abutBottom(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - self.left())
        dy = int(other.bottom() - space - self.top())
        self.translate(dx, dy)
        return self

    def abutTop(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - self.left())
        dy = int(other.top() + space - self.bottom())
        self.translate(dx, dy)
        return self

    def abutLeft(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - space - self.right())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def abutRight(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.right() + space - self.left())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def moveBelow(self, other, ygap=0):
        return self.abutBottom(other, ygap)

    def moveAbove(self, other, ygap=0):
        return self.abutTop(other, ygap)

    def _tap_name(self, cell_name, suffix):
        #- the trailing D of a diode connected variant is not part of
        #- the width class, and the tap does not have one
        return re.sub(r"C\d+F\d+D?$", suffix, cell_name)

    def _resolve_tap_cell(self, cell_name, suffix):
        """Return the name of a tap cell that actually exists, or None.

        The tap ring carries no gate, so a device variant marker like LVT has
        no tap counterpart in the libraries. When the directly derived name is
        missing, retry without the variant marker, so an LVT stack picks up
        the plain tap of the same width class.
        """
        candidates = [self._tap_name(cell_name, suffix)]
        stripped = re.sub(r"(?<=_)LVT_", "", cell_name, count=1)
        if stripped != cell_name:
            candidates.append(self._tap_name(stripped, suffix))
        for cand in candidates:
            if cand == cell_name:
                continue
            if self.layout.parent.getLayoutCell(cand) is not None:
                return cand
        return None

    def routeDummyTerminals(self, inst):
        """Lay a single M1 strap rectangle across the middle of a filler
        transistor.

        The strap is plain geometry, not a route — fillers don't need the
        three-primitive routing contract; they just need a body-tie-friendly
        M1 conductor across the device. One rect per filler.
        """
        if inst is None:
            return self
        rules = Rules.getInstance()
        if rules is not None and rules.hasRules():
            width = rules.get("M1", "width")
        else:
            width = 320
        cy = int(inst.centerY())
        rect = Rect("M1", int(inst.x1), cy - width // 2, int(inst.width()), int(width))
        #- The strap belongs to the stack, like the filler it covers. Left in
        #- the layout's placement tree as well it is translated twice on
        #- resetOrigin, once as a layout child and once through the stack's
        #- dummy_routes, which threw every strap far outside the cell
        self.layout.add(rect)
        self.layout.detachPlacementChild(rect, keepParent=self)
        self.add(rect)
        self.dummy_routes.append(rect)
        self.updateBoundingRect()
        return self

    def addTaps(self, prefix=None):
        if not self.instances:
            return self
        self.sort()
        base = self.instances[0]
        bot_cell = self._resolve_tap_cell(base.cell, "CTAPBOT")
        top_cell = self._resolve_tap_cell(base.cell, "CTAPTOP")
        if bot_cell is None or top_cell is None:
            self.layout.log.warning(
                f"No tap cells found for {base.cell}, stack {self.name} is left untapped")
            return self
        name = prefix or self.name
        bot = self.layout.addPhysicalInstance(bot_cell, f"xstack_{name}_bot", int(base.x1), int(base.y1 - 24000))
        top = self.layout.addPhysicalInstance(top_cell, f"xstack_{name}_top", int(base.x1), int(self.instances[-1].y2))
        if bot is not None and bot not in self.tap_instances:
            self.tap_instances.append(bot)
            self.layout.detachPlacementChild(bot, keepParent=self)
            self.add(bot)
        if top is not None and top not in self.tap_instances:
            self.tap_instances.append(top)
            self.layout.detachPlacementChild(top, keepParent=self)
            self.add(top)
        self.updateBoundingRect()
        return self

    def routeDummyDevices(self):
        for inst in list(self.instances):
            inst_name = getattr(inst, "instanceName", "") or ""
            if not inst_name.startswith("xfill_"):
                continue
            self.routeDummyTerminals(inst)
        self.updateBoundingRect()
        return self

    def mirror(self):
        """Mirror every device and tap in the stack about its own vertical
        axis.

        A matched pair of columns wants the mirrored arrangement, the two
        halves then share their seam with mirror symmetric edge geometry
        instead of repeating the same edge, which is what allows them to sit
        closer than two identical columns can.
        """
        for inst in self.instances + self.tap_instances:
            #- setAngle leaves the instance position in the mirrored frame,
            #- the printer recovers through xcell but every bounding box
            #- consumer would not, so pin the instance back where it was
            x, y = inst.x1, inst.y1
            inst.setAngle("MY")
            inst.moveTo(int(x), int(y))
            inst.updateBoundingRect()
        self.updateBoundingRect()
        return self

    def _get_or_create_dummy(self, base, dname, x, y):
        dummy = self.layout.getInstanceFromInstanceName(dname)
        if dummy is None:
            dummy = self.layout.addPhysicalInstance(base.cell, dname, int(x), int(y))
        else:
            dummy.moveTo(int(x), int(y))
            dummy.updateBoundingRect()
        return dummy

    def fillDummyTransistors(self, target_height, direction="top"):
        if not self.instances:
            return self
        self.sort()
        current_height = self.height()
        if current_height >= target_height:
            return self
        base = self.instances[0]
        dummy_index = 0
        if direction == "bottom":
            ypos = int(self.bottom())
            while current_height < target_height:
                dname = f"xfill_{self.name}_{dummy_index}"
                dummy = self._get_or_create_dummy(base, dname, int(base.x1), int(ypos - base.height()))
                if dummy is None:
                    break
                self.addInstance(dummy)
                ypos = int(dummy.y1)
                current_height = self.height()
                dummy_index += 1
        else:
            ypos = int(self.top())
            while current_height < target_height:
                dname = f"xfill_{self.name}_{dummy_index}"
                dummy = self._get_or_create_dummy(base, dname, int(base.x1), ypos)
                if dummy is None:
                    break
                self.addInstance(dummy)
                ypos = int(dummy.y2)
                current_height = self.height()
                dummy_index += 1
        self.sort()
        self.updateBoundingRect()
        return self

    def exportedPorts(self):
        return self.exportBoundaryPorts()

    def toJson(self):
        return {
            "class": "StackGroup",
            "name": self.name,
            "kind": self.kind,
            "bbox": _bbox_json(self),
            "ports": _ports_json(self.exportedPorts()),
            "preserve_order": self.preserve_order,
            "instances": [getattr(i, "instanceName", "") for i in self.instances],
            "tap_instances": [getattr(i, "instanceName", "") for i in self.tap_instances],
            "route_bundles": [b.toJson() for b in self.route_bundles],
        }
