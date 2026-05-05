#!/usr/bin/env python3

import re

from .cell import Cell
from .port import Port
from .rect import Rect
from .route import Route


class _PhysicalInst:
    def __init__(self, name, subckt_name):
        self.name = name
        self.subcktName = subckt_name


class ParallelGroup(Cell):
    def __init__(self, layout, name, instances):
        super().__init__(name)
        self.layout = layout
        self.instances = list(instances or [])
        self.route_rects = []
        self.group_ports = {}

    def _members(self):
        return self.instances + self.route_rects + list(self.group_ports.values())

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
        self.layout.add(rect)
        self.updateBoundingRect()
        return rect

    def addGroupPort(self, net, rect, edge):
        port = Port(net, routeLayer=rect.layer, rect=rect)
        port.spicePort = False
        port.side = edge
        self.group_ports[net] = port
        self.add(port)
        self.updateBoundingRect()
        return port

    def representativeAccessRects(self, net, accessLayer=None):
        port = self.group_ports.get(net)
        if port is None:
            return []
        rect = port.get(accessLayer)
        return [rect] if rect is not None else []


class StackGroup(Cell):
    def __init__(self, layout, name):
        super().__init__(name)
        self.layout = layout
        self.instances = []
        self.tap_instances = []
        self.dummy_routes = []
        self.direct_routes = []
        self.diode_routes = []
        self.parallel_groups = []
        self.preserve_order = False

    def _members(self):
        members = []
        seen = set()
        for obj in (
            self.instances
            + self.tap_instances
            + self.dummy_routes
            + self.direct_routes
            + self.parallel_groups
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

    def addOrthogonalConnectivityRoute(self, verticalLayer, horizontalLayer, regex, options="", cuts=1, excludeInstances="", accessLayer=None):
        include = self.instanceRegex()
        self.layout.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, include, accessLayer=accessLayer)
        return self

    def representativeAccessRects(self, net, accessLayer, anymetal=False):
        rects = []
        for group in self.parallel_groups:
            rects.extend(group.representativeAccessRects(net, accessLayer))
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
            access = inst.getTerminalAccess(terminal_name, target_layer=accessLayer)
            if access is None or access.isEmpty():
                continue
            rect = access.primary(anymetal=anymetal)
            if rect is None:
                continue
            rects.append(rect)
        rects = self.layout.collapseRepresentativeRects(net, rects)
        if not rects:
            return []
        target_y = 0.5 * (self.bottom() + self.top())
        chosen = min(rects, key=lambda r: (abs(r.centerY() - target_y), abs(r.centerX() - self.left()), r.x1, r.y1))
        return [chosen]

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
            out.append(ParallelGroup(self.layout, f"{self.name}_{name}", instances))
        return out

    def _ports_by_net(self, instances, terminals=None, layer="M2", excludeInstances="", excludeNets="", sameTerminal=True):
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
                access = inst.getTerminalAccess(terminal_name, target_layer=layer)
                if access is None:
                    continue
                rect = self._choose_access_rect(access, axis="x")
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

    def _vertical_parallel_rect(self, layer, rects):
        if not rects:
            return None
        source = sorted(rects, key=lambda r: (r.y1, r.x1))[0]
        y1 = min(r.y1 for r in rects)
        y2 = max(r.y2 for r in rects)
        rect = Rect(layer, source.x1, y1, source.width(), y2 - y1)
        rect.net = getattr(source, "net", "")
        return rect

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

    def _direct_tie_rect(self, layer, first, second, routeType=""):
        if first is None or second is None:
            return None
        y1 = max(first.y1, second.y1)
        y2 = min(first.y2, second.y2)
        if y2 > y1 and routeType in ("", "-", "-|--", "--|-"):
            x1 = min(first.x1, second.x1)
            x2 = max(first.x2, second.x2)
            return Rect(layer, x1, y1, x2 - x1, y2 - y1)
        x1 = max(first.x1, second.x1)
        x2 = min(first.x2, second.x2)
        if x2 > x1 and routeType in ("", "||", "-|--", "--|-"):
            y1 = min(first.y1, second.y1)
            y2 = max(first.y2, second.y2)
            return Rect(layer, x1, y1, x2 - x1, y2 - y1)
        return None

    def _add_direct_route_rect(self, rect, is_diode=False):
        self.direct_routes.append(rect)
        if is_diode:
            self.diode_routes.append(rect)
        self.add(rect)
        self.layout.add(rect)
        self.updateBoundingRect()
        return rect

    def _add_direct_route_between(self, layer, net, start_rect, stop_rect, routeType="", is_diode=False, route_desc=""):
        route_rect = self._direct_tie_rect(layer, start_rect, stop_rect, routeType=routeType)
        if route_rect is None:
            return None
        route_rect.net = net
        if route_desc:
            route_rect.route_owner_info = {
                "name": net,
                "net": net,
                "layer": layer,
                "route": route_desc,
                "options": "",
                "debug_api": "routeDiodeConnected" if is_diode else "directRouteRect",
                "debug_internal": False,
            }
        return self._add_direct_route_rect(route_rect, is_diode=is_diode)

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
        """Join repeated device terminals inside the stack and expose one group port per net.

        The method prefers existing terminal access on ``layer``. For a vertical
        transistor stack that normally means extending the device M2 access into a
        single trunk and placing one access rectangle on a group edge.
        """
        for group in self._parallel_instance_groups(excludeInstances=excludeInstances):
            nets = self._ports_by_net(group.instances, terminals=terminals, layer=layer, excludeInstances=excludeInstances, excludeNets=excludeNets, sameTerminal=sameTerminal)
            required_rects = minRects if minRects is not None else len(group.instances)
            required_rects = max(2, required_rects)
            for net, (terminal_name, rects) in nets.items():
                if len(rects) < required_rects:
                    continue
                route_rect = self._vertical_parallel_rect(layer, rects)
                if route_rect is None:
                    continue
                route_rect.net = net
                group.addRouteRect(route_rect)

                port_edge = edges.get(net, edge) if edges else edge
                port_rect = self._edge_port_rect(layer, route_rect, port_edge, rects[0].height())
                if port_rect is None:
                    continue
                port_rect.net = net
                group.addGroupPort(net, port_rect, port_edge)

            if group.route_rects:
                self.parallel_groups.append(group)
                self.add(group)
        self.updateBoundingRect()
        return self

    def routeMirror(self, layer="M2", terminals=("G", "S"), edge="top", edges=None, excludeInstances="^xfill_", excludeNets="", minRects=2, sameTerminal=True):
        """Route common mirror terminals inside the stack.

        Current mirror stacks normally share gate and source nets while each
        drain remains distinct. This helper routes only common terminals from
        ``terminals`` across the whole stack and exposes one nested group port
        per routed net.
        """
        instances = self._route_instances_excluding(excludeInstances=excludeInstances)
        if len(instances) < 2:
            return self
        group = ParallelGroup(self.layout, f"{self.name}_mirror", sorted(instances, key=lambda inst: (inst.y1, inst.x1, getattr(inst, "instanceName", ""))))
        nets = self._ports_by_net(group.instances, terminals=terminals, layer=layer, excludeInstances=excludeInstances, excludeNets=excludeNets, sameTerminal=sameTerminal)
        required_rects = minRects if minRects is not None else 2
        required_rects = max(2, required_rects)
        for net, (terminal_name, rects) in nets.items():
            if len(rects) < required_rects:
                continue
            route_rect = self._vertical_parallel_rect(layer, rects)
            if route_rect is None:
                continue
            route_rect.net = net
            group.addRouteRect(route_rect)

            port_edge = edges.get(net, edge) if edges else ("middle" if terminal_name == "S" else edge)
            port_rect = self._edge_port_rect(layer, route_rect, port_edge, rects[0].height())
            if port_rect is None:
                continue
            port_rect.net = net
            group.addGroupPort(net, port_rect, port_edge)

        if group.route_rects:
            self.parallel_groups.append(group)
            self.add(group)
        self.updateBoundingRect()
        return self

    def routeDiodeConnected(self, layer="M1", drain="D", gate="G", excludeInstances=""):
        """Tie diode-connected transistor drain and gate on the lowest local layer.

        A transistor is treated as diode-connected when its drain and gate
        terminals are on the same schematic net. Bulk is ignored.
        """
        for inst in self._route_instances():
            instance_name = getattr(inst, "instanceName", "")
            if excludeInstances and (
                re.search(excludeInstances, instance_name) or re.search(excludeInstances, getattr(inst, "name", ""))
            ):
                continue

            drain_net = self._terminal_net(inst, drain)
            gate_net = self._terminal_net(inst, gate)
            if not drain_net or drain_net != gate_net:
                continue

            drain_access = inst.getTerminalAccess(drain, target_layer=layer)
            gate_access = inst.getTerminalAccess(gate, target_layer=layer)
            drain_rect = self._choose_access_rect(drain_access, axis="x")
            gate_rect = self._choose_access_rect(gate_access, reference=drain_rect, axis="y")
            if drain_rect is None or gate_rect is None:
                continue
            if getattr(drain_rect, "layer", "") != layer or getattr(gate_rect, "layer", "") != layer:
                continue

            route_desc = f"{instance_name}:{drain}-{instance_name}:{gate}"
            self._add_direct_route_between(layer, drain_net, drain_rect, gate_rect, routeType="-", is_diode=True, route_desc=route_desc)
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
        self.add(inst)
        self.updateBoundingRect()
        return inst

    def addInstances(self, instances):
        for inst in instances:
            self.addInstance(inst)
        self.updateBoundingRect()
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
            return super().calcBoundingRect()
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

    # Compatibility aliases
    def moveBelow(self, other, ygap=0):
        return self.abutBottom(other, ygap)

    def moveAbove(self, other, ygap=0):
        return self.abutTop(other, ygap)

    def _tap_name(self, cell_name, suffix):
        return re.sub(r"C\d+F\d+$", suffix, cell_name)

    def _overlap_amount(self, a, b, axis="y"):
        if a is None or b is None:
            return 0
        if axis == "x":
            return max(0, min(a.x2, b.x2) - max(a.x1, b.x1))
        return max(0, min(a.y2, b.y2) - max(a.y1, b.y1))

    def _choose_access_rect(self, access, reference=None, axis="y", prefer_lower=True):
        if access is None or not access.accessRects:
            return None
        if reference is None:
            rects = sorted(access.accessRects, key=lambda r: (r.y1, r.x1))
            return rects[0] if prefer_lower else rects[-1]

        def score(rect):
            overlap = self._overlap_amount(rect, reference, axis)
            distance = abs(rect.centerY() - reference.centerY()) + abs(rect.centerX() - reference.centerX())
            tie = rect.y1 if prefer_lower else -rect.y2
            return (-overlap, distance, tie, rect.x1)

        return sorted(access.accessRects, key=score)[0]

    def _add_dummy_route(self, net_name, route_layer, start_rects, stop_rects, route_type):
        if not start_rects or not stop_rects:
            return None
        route = Route(net_name, route_layer, start_rects, stop_rects, "", route_type)
        if hasattr(self.layout, "_annotateRoute"):
            self.layout._annotateRoute(route, "routeDummyTerminals", {
                "stack": self.name,
                "net": net_name,
                "layer": route_layer,
                "routeType": route_type,
                "internal": True,
            })
        self.layout.add(route)
        self.dummy_routes.append(route)
        return route

    def routeDummyTerminals(self, inst):
        if inst is None:
            return self

        d_access = inst.getTerminalAccess("D", target_layer="M1")
        g_access = inst.getTerminalAccess("G", target_layer="M1")
        s_access = inst.getTerminalAccess("S", target_layer="M1")
        b_access = inst.getTerminalAccess("B", target_layer="M1")
        if d_access is None or g_access is None or s_access is None or b_access is None:
            return self
        if d_access.isEmpty() or g_access.isEmpty() or s_access.isEmpty() or b_access.isEmpty():
            return self

        d_rect = self._choose_access_rect(d_access)
        g_rect = self._choose_access_rect(g_access, reference=d_rect)
        s_rect = self._choose_access_rect(s_access, reference=d_rect, prefer_lower=True)
        b_mid = self._choose_access_rect(b_access, reference=d_rect)
        b_side = self._choose_access_rect(b_access, reference=s_rect)

        if d_rect is None or g_rect is None or s_rect is None or b_mid is None or b_side is None:
            return self

        base = inst.instanceName or inst.name or self.name
        self._add_dummy_route(f"{base}_dummy_mid", "M1", [b_mid], [d_rect], "-")
        self._add_dummy_route(f"{base}_dummy_side", "M1", [b_side], [s_rect], "-")
        self._add_dummy_route(f"{base}_dummy_vert", "M1", [d_rect], [s_rect], "||")
        self.updateBoundingRect()
        return self

    def addTaps(self, prefix=None):
        if not self.instances:
            return self
        self.sort()
        base = self.instances[0]
        bot_cell = self._tap_name(base.cell, "CTAPBOT")
        top_cell = self._tap_name(base.cell, "CTAPTOP")
        if bot_cell == base.cell or top_cell == base.cell:
            return self
        name = prefix or self.name
        bot = self.layout.addPhysicalInstance(bot_cell, f"xstack_{name}_bot", int(base.x1), int(base.y1 - 24000))
        top = self.layout.addPhysicalInstance(top_cell, f"xstack_{name}_top", int(base.x1), int(self.instances[-1].y2))
        if bot is not None and bot not in self.tap_instances:
            self.tap_instances.append(bot)
            self.add(bot)
        if top is not None and top not in self.tap_instances:
            self.tap_instances.append(top)
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


class CellGroup(Cell):
    def __init__(self, layout, name):
        super().__init__(name)
        self.layout = layout
        self.stacks = []

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

    def addOrthogonalConnectivityRoute(self, verticalLayer, horizontalLayer, regex, options="", cuts=1, excludeInstances="", accessLayer=None):
        include = self.instanceRegex()
        self.layout.addOrthogonalConnectivityRoute(verticalLayer, horizontalLayer, regex, options, cuts, excludeInstances, include, accessLayer=accessLayer)
        return self

    def representativeAccessRects(self, net, accessLayer, anymetal=False):
        rects = []
        for stack in self.stacks:
            rects.extend(stack.representativeAccessRects(net, accessLayer, anymetal=anymetal))
        return self.layout.collapseRepresentativeRects(net, rects)

    def addStack(self, name, instances, preserveOrder=False):
        stack = StackGroup(self.layout, name)
        stack.preserve_order = preserveOrder
        stack.addInstances(instances)
        self.stacks.append(stack)
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

    # Compatibility aliases
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
