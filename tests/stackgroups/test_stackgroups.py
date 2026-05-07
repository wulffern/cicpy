from cicpy.core.instance import Instance
from cicpy.core.layoutcell import LayoutCell
from cicpy.core.port import Port
from cicpy.core.rect import Rect


# Synthetic per-terminal x offsets — chosen so that the bulk-port boundary
# tests can distinguish the bulk contact (x=80) from the source pin (x=60).
TERMINAL_X = {"D": 20, "G": 40, "S": 60, "B": 80}


def add_instance(layout, name, width=100, height=100):
    """Create a synthetic Instance with a real bounding box.

    Tests previously decoupled rect lookup (via a stubbed
    ``getTerminalAccess`` lambda) from instance position, so zero-sized
    instances were fine. Now ``port.get`` reads the actual port child of
    the instance, and ``stack().stack()`` translates ports with the
    instance — so each instance needs a non-zero bbox for stacking to
    place ports at distinct y values.
    """
    inst = Instance()
    inst.instanceName = name
    inst.name = "DUMMY"
    layout.add(inst)
    if width or height:
        inst.setPoint1(0, 0)
        inst.setPoint2(width, height)
    return inst


def add_terminals(inst, terminals, layer, x=None, y=None):
    """Attach real Port objects to ``inst`` for each named terminal.

    Coordinates default to the instance's current x1/y1; the per-terminal
    x offset comes from ``TERMINAL_X``. Use this in place of the old
    ``getTerminalAccess`` lambdas.
    """
    if x is None:
        x = inst.x1
    if y is None:
        y = inst.y1
    for t in terminals:
        tx = x + TERMINAL_X.get(t, 80)
        inst.add(Port(t, routeLayer=layer, rect=Rect(layer, tx, y, 10, 10)))


def port_stub(parent, terminal):
    """Graph-node port stub. ``.get(layer)`` reads ``parent.getPort(terminal)``
    so the stub mirrors the production lookup path used by
    ``LayoutCell.getNodeAccessRects`` and ``StackGroup._ports_by_net``.
    """
    p = type("Port", (), {})()
    p.parent = parent
    p.childName = terminal

    def _get(layer=None, _parent=parent, _term=terminal):
        port = _parent.getPort(_term) if hasattr(_parent, "getPort") else None
        if port is None or not hasattr(port, "get"):
            return None
        rr = port.get(layer)
        if rr is None:
            rr = port.get()
        if rr is None:
            return None
        if layer and getattr(rr, "layer", "") and getattr(rr, "layer", "") != layer:
            return None
        return rr

    p.get = _get
    return p


# ---- 1. Group-name lookup and stack ownership --------------------------------
layout = LayoutCell()
for name in [
    "xn_a10",
    "xn_a2<3>",
    "xn_a2<1>",
    "xfill_xn_a1<0>",
    "xn_a2<0>",
    "xn_a1",
    "xn_ab1",
]:
    add_instance(layout, name)

assert [i.instanceName for i in layout.getSortedInstancesByGroupName("xn_a")] == [
    "xn_a1",
    "xn_a2<0>",
    "xn_a2<1>",
    "xn_a2<3>",
    "xn_a10",
]

assert [i.instanceName for i in layout.getSortedInstancesByGroupName("xn_a", excludeInstances="^xn_a2")] == [
    "xn_a1",
    "xn_a10",
]

group = layout.makeCellGroup("nmos")
stack = group.addStackByGroup("xn_a", fillGroup="xfill_xn_a")
assert group in layout.children
assert [i.instanceName for i in stack.instances] == [
    "xn_a1",
    "xn_a2<0>",
    "xn_a2<1>",
    "xn_a2<3>",
    "xn_a10",
    "xfill_xn_a1<0>",
]
assert all(i not in layout.children for i in stack.instances)
stack.stack()
assert [i.instanceName for i in sorted(stack.instances, key=lambda i: i.y1)] == [
    "xn_a1",
    "xn_a2<0>",
    "xn_a2<1>",
    "xn_a2<3>",
    "xn_a10",
    "xfill_xn_a1<0>",
]

# ---- 2. routeParallel: trunk + bundle port -----------------------------------
parallel_layout = LayoutCell()
parallel_insts = []
for idx in range(3):
    inst = add_instance(parallel_layout, f"xp_par1<{idx}>")
    inst.moveTo(0, idx * 100)
    add_terminals(inst, ("D", "S"), "M2")
    parallel_insts.append(inst)
parallel_outside = add_instance(parallel_layout, "xout")
parallel_outside.moveTo(200, 500)
parallel_outside.add(Port("D", routeLayer="M2", rect=Rect("M2", 200, 500, 10, 10)))

parallel_layout.nodeGraph = {
    "VPAR": type("Node", (), {"ports": []})(),
    "VSER": type("Node", (), {"ports": []})(),
    "VSS": type("Node", (), {"ports": []})(),
}
parallel_layout.nodeGraphList = list(parallel_layout.nodeGraph.keys())
for inst in parallel_insts:
    parallel_layout.nodeGraph["VPAR"].ports.append(port_stub(inst, "D"))
    parallel_layout.nodeGraph["VSS"].ports.append(port_stub(inst, "S"))
parallel_layout.nodeGraph["VPAR"].ports.append(port_stub(parallel_outside, "D"))
for inst in parallel_insts[:2]:
    parallel_layout.nodeGraph["VSER"].ports.append(port_stub(inst, "D"))

parallel_group = parallel_layout.makeCellGroup("pmos")
parallel_stack = parallel_group.addParallelStack("par", parallel_insts).stack().routeParallel()
assert len(parallel_stack.parallel_groups) == 1
parallel_bus = parallel_stack.parallel_groups[0]
assert "VPAR" in parallel_bus.group_ports
assert "VSER" not in parallel_bus.group_ports
assert "VSS" in parallel_bus.group_ports
assert len(parallel_bus.route_rects) == 2
assert parallel_bus.route_rects[0] in parallel_bus.children
assert parallel_bus.route_rects[0] not in parallel_layout.children
assert parallel_bus.route_rects[0].width() == 10
assert parallel_bus.route_rects[0].height() == 210
assert {p.name for p in parallel_stack.exportBoundaryPorts(layer="M2")} == {"VPAR"}
assert {p.name for p in parallel_group.exportBoundaryPorts(layer="M2")} == {"VPAR"}
top_rects = parallel_layout.getNodeAccessRects("VPAR", "M2")
assert len(top_rects) == 2
assert any(r.x1 == 200 and r.y1 == 500 for r in top_rects)
direct_rects = parallel_layout.getNodeAccessRects("VPAR", "M2", includeInstances="^xp_par")
assert len(direct_rects) == 3
parallel_layout.addConnectivityRoute("M2", "^VPAR$", "||", "", 1, "", "")
route_rects = parallel_layout.routes[-1].startRects + parallel_layout.routes[-1].stopRects
assert len(route_rects) == 2
assert any(r.x1 == 200 and r.y1 == 500 for r in route_rects)
internal_check = parallel_stack.checkInternalConnectivity(warnOnly=True)
assert "VSER" in internal_check["opens"]
assert "VSS" not in internal_check["opens"]
assert "VSS" not in internal_check["boundary_nets"]

# ---- 3. exportBoundaryPorts onTopLeft / onTopRight selectors -----------------
selector_layout = LayoutCell()
selector_group = selector_layout.makeCellGroup("selector")
selector_layout.nodeGraph = {"VSEL": type("Node", (), {"ports": []})()}
selector_layout.nodeGraphList = ["VSEL"]
for name, x, y in (("xsel_a", 0, 0), ("xsel_b", 0, 100), ("xsel_c", 100, 100)):
    inst = add_instance(selector_layout, name)
    inst.moveTo(x, y)
    # Each selector instance only exposes a "D" port at its own (x, y).
    inst.add(Port("D", routeLayer="M2", rect=Rect("M2", x, y, 10, 10)))
    selector_layout.nodeGraph["VSEL"].ports.append(port_stub(inst, "D"))
    # Single-instance stack — skip .stack() so the explicit (x, y) is preserved.
    selector_group.addStack(name, [inst])
selector_outside = add_instance(selector_layout, "xsel_out")
selector_outside.add(Port("D", routeLayer="M2", rect=Rect("M2", 200, 0, 10, 10)))
selector_layout.nodeGraph["VSEL"].ports.append(port_stub(selector_outside, "D"))
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopLeft")[0].x1 == 0
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopLeft")[0].y1 == 100
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopRight")[0].x1 == 100
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopRight")[0].y1 == 100

# ---- 4. exportBoundaryPorts: bulk vs source default --------------------------
bulk_layout = LayoutCell()
bulk_group = bulk_layout.makeCellGroup("bulk")
bulk_layout.nodeGraph = {"VSS": type("Node", (), {"ports": []})()}
bulk_layout.nodeGraphList = ["VSS"]
for idx in range(2):
    inst = add_instance(bulk_layout, f"xn_bulk{idx}")
    inst.moveTo(0, idx * 100)
    add_terminals(inst, ("S", "B"), "M2")
    bulk_layout.nodeGraph["VSS"].ports.append(port_stub(inst, "S"))
    bulk_layout.nodeGraph["VSS"].ports.append(port_stub(inst, "B"))
    # Single-instance stack — skip .stack() so the explicit y is preserved.
    bulk_group.addStack(f"bulk{idx}", [inst])
bulk_outside = add_instance(bulk_layout, "xbulk_out")
bulk_outside.add(Port("S", routeLayer="M2", rect=Rect("M2", 200, 0, 10, 10)))
bulk_layout.nodeGraph["VSS"].ports.append(port_stub(bulk_outside, "S"))
default_bulk_ports = bulk_group.exportBoundaryPorts(layer="M2")
assert len(default_bulk_ports) == 1
assert default_bulk_ports[0].x1 == 60
assert bulk_group.exportBoundaryPorts(layer="M2", options="bulk")[0].x1 == 80
assert bulk_group.exportBoundaryPorts(layer="M2", options="terminal=B")[0].x1 == 80
bulk_top_rects = bulk_layout.getNodeAccessRects("VSS", "M2")
# With no internal routing for VSS in the bulk_group stacks, member pins
# are not suppressed — both source (x=60) and bulk (x=80) surface for the
# parent route engine. The boundary "nonbulk" preference still applies to
# exportBoundaryPorts directly (covered above).
assert any(r.x1 == 60 for r in bulk_top_rects)
assert any(r.x1 == 80 for r in bulk_top_rects)

# ---- 5. transistorStack with shared gate net (parallel routing) --------------
transistor_layout = LayoutCell()
for idx in range(2):
    inst = add_instance(transistor_layout, f"xn_t1<{idx}>")
    inst.moveTo(0, idx * 100)
    add_terminals(inst, ("G",), "M2")
transistor_layout.nodeGraph = {"VT": type("Node", (), {"ports": []})()}
for inst in transistor_layout.children:
    transistor_layout.nodeGraph["VT"].ports.append(port_stub(inst, "G"))

transistor_group = transistor_layout.makeCellGroup("nmos")
transistor_stack = transistor_group.transistorStack("xn_t")
assert len(transistor_stack.parallel_groups) == 1
assert "VT" in transistor_stack.parallel_groups[0].group_ports

# ---- 6. routeDiodeConnected: D-G tie via addDirectedRoute --------------------
diode_layout = LayoutCell()
diode_inst = add_instance(diode_layout, "xn_diode1")
add_terminals(diode_inst, ("D", "G"), "M1")
diode_layout.nodeGraph = {"VDIO": type("Node", (), {"ports": []})()}
diode_layout.nodeGraph["VDIO"].ports.append(port_stub(diode_inst, "D"))
diode_layout.nodeGraph["VDIO"].ports.append(port_stub(diode_inst, "G"))

diode_group = diode_layout.makeCellGroup("nmos")
diode_stack = diode_group.transistorStack("xn_diode")
assert len(diode_stack.diode_routes) == 1
diode_route = diode_stack.diode_routes[0]
assert diode_route.routeLayer == "M1"
assert diode_route.net == "VDIO"
# Routes live in the layout's children; the stack tracks them through the
# diode_routes / direct_routes side-lists so JSON / connectivity walks see
# them without re-parenting the Route under the stack.
assert diode_route in diode_layout.children
assert diode_route in diode_layout.routes

# ---- 7. currentMirrorStack: shared G/S, distinct D ---------------------------
mirror_layout = LayoutCell()
mirror_insts = []
for idx in range(3):
    inst = add_instance(mirror_layout, f"xp_mirr{idx + 1}")
    inst.moveTo(0, idx * 100)
    add_terminals(inst, ("D", "G", "S"), "M2")
    mirror_insts.append(inst)
mirror_outside = add_instance(mirror_layout, "xbias")
mirror_outside.moveTo(200, 500)
mirror_outside.add(Port("G", routeLayer="M2", rect=Rect("M2", 200, 500, 10, 10)))
mirror_outside.add(Port("S", routeLayer="M2", rect=Rect("M2", 200, 500, 10, 10)))
mirror_layout.nodeGraph = {
    "VG": type("Node", (), {"ports": []})(),
    "VS": type("Node", (), {"ports": []})(),
    "VD0": type("Node", (), {"ports": []})(),
    "VD1": type("Node", (), {"ports": []})(),
    "VD2": type("Node", (), {"ports": []})(),
}
for idx, inst in enumerate(mirror_insts):
    mirror_layout.nodeGraph["VG"].ports.append(port_stub(inst, "G"))
    mirror_layout.nodeGraph["VS"].ports.append(port_stub(inst, "S"))
    mirror_layout.nodeGraph[f"VD{idx}"].ports.append(port_stub(inst, "D"))
mirror_layout.nodeGraph["VG"].ports.append(port_stub(mirror_outside, "G"))
mirror_layout.nodeGraph["VS"].ports.append(port_stub(mirror_outside, "S"))

mirror_group = mirror_layout.makeCellGroup("pmos")
mirror_stack = mirror_group.currentMirrorStack("xp_mirr")
assert len(mirror_stack.parallel_groups) == 1
mirror_bus = mirror_stack.parallel_groups[0]
assert "VG" in mirror_bus.group_ports
assert "VS" in mirror_bus.group_ports
assert "VD0" not in mirror_bus.group_ports
assert len(mirror_bus.route_rects) == 2
source_route = [r for r in mirror_bus.route_rects if r.net == "VS"][0]
source_port = mirror_bus.group_ports["VS"].get("M2")
assert source_port.centerY() == source_route.centerY()
hierarchy = mirror_layout.toJson()["cellgroups"]
json_instance_names = [
    child.get("instanceName", "")
    for child in mirror_layout.toJson()["children"]
    if child.get("class") == "Instance"
]
assert json_instance_names == ["xbias", "xp_mirr1", "xp_mirr2", "xp_mirr3"]
assert hierarchy[0]["class"] == "CellGroup"
assert hierarchy[0]["name"] == "pmos"
assert hierarchy[0]["bbox"]["x2"] > hierarchy[0]["bbox"]["x1"]
assert {p["name"] for p in hierarchy[0]["ports"]} == {"VG", "VS"}
assert hierarchy[0]["stacks"][0]["class"] == "StackGroup"
assert hierarchy[0]["stacks"][0]["kind"] == "mirrorStack"
assert hierarchy[0]["stacks"][0]["instances"] == ["xp_mirr1", "xp_mirr2", "xp_mirr3"]
assert {p["name"] for p in hierarchy[0]["stacks"][0]["ports"]} == {"VG", "VS"}
assert hierarchy[0]["stacks"][0]["route_bundles"][0]["class"] == "RouteBundle"
loaded_layout = LayoutCell()
loaded_layout.design = type("Design", (), {"prefix": ""})()
loaded_layout.fromJson(mirror_layout.toJson())
assert loaded_layout.guiHierarchy == hierarchy
assert loaded_layout.toJson()["cellgroups"] == hierarchy

with open("stackgroups.status", "w", encoding="utf-8") as fh:
    fh.write("stack group helper test passed\n")
