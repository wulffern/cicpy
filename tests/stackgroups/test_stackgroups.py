from cicpy.core.instance import Instance
from cicpy.core.instance import TerminalAccess
from cicpy.core.layoutcell import LayoutCell
from cicpy.core.rect import Rect


def add_instance(layout, name):
    inst = Instance()
    inst.instanceName = name
    inst.name = "DUMMY"
    layout.add(inst)
    return inst


def port_stub(parent, terminal):
    """Graph-node port stub with a real ``.get(layer)`` that mirrors a real
    Port. Production code no longer falls back through ``getTerminalAccess``,
    so the stub provides a rect via ``parent.getTerminalAccess`` (which the
    test still stubs per-instance) until Step 6 drops that path entirely.
    """
    p = type("Port", (), {})()
    p.parent = parent
    p.childName = terminal

    def _get(layer=None, _parent=parent, _term=terminal):
        get_access = getattr(_parent, "getTerminalAccess", None)
        if get_access is None:
            return None
        access_obj = get_access(_term, target_layer=layer or "M2")
        if access_obj is None or not getattr(access_obj, "accessRects", []):
            return None
        rect = access_obj.accessRects[0]
        if layer and getattr(rect, "layer", "") != layer:
            return None
        return rect

    p.get = _get
    return p


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


def access(layer, terminal, y):
    x_by_terminal = {"D": 20, "G": 40, "S": 60}
    x = x_by_terminal.get(terminal, 80)
    return TerminalAccess(terminal, layer, layer, None, [], [Rect(layer, x, y, 10, 10)])


parallel_layout = LayoutCell()
parallel_insts = []
for idx in range(3):
    inst = add_instance(parallel_layout, f"xp_par1<{idx}>")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
    parallel_insts.append(inst)
parallel_outside = add_instance(parallel_layout, "xout")
parallel_outside.moveTo(200, 500)
parallel_outside.getTerminalAccess = lambda terminal, target_layer="M2": TerminalAccess(terminal, target_layer, target_layer, None, [], [Rect(target_layer, 200, 500, 10, 10)])

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

selector_layout = LayoutCell()
selector_group = selector_layout.makeCellGroup("selector")
selector_layout.nodeGraph = {"VSEL": type("Node", (), {"ports": []})()}
selector_layout.nodeGraphList = ["VSEL"]
for name, x, y in (("xsel_a", 0, 0), ("xsel_b", 0, 100), ("xsel_c", 100, 100)):
    inst = add_instance(selector_layout, name)
    inst.moveTo(x, y)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", x=x, y=y: TerminalAccess(terminal, target_layer, target_layer, None, [], [Rect(target_layer, x, y, 10, 10)])
    selector_layout.nodeGraph["VSEL"].ports.append(port_stub(inst, "D"))
    selector_group.addStack(name, [inst]).stack()
selector_outside = add_instance(selector_layout, "xsel_out")
selector_outside.getTerminalAccess = lambda terminal, target_layer="M2": TerminalAccess(terminal, target_layer, target_layer, None, [], [Rect(target_layer, 200, 0, 10, 10)])
selector_layout.nodeGraph["VSEL"].ports.append(port_stub(selector_outside, "D"))
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopLeft")[0].x1 == 0
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopLeft")[0].y1 == 100
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopRight")[0].x1 == 100
assert selector_group.exportBoundaryPorts(layer="M2", options="onTopRight")[0].y1 == 100

bulk_layout = LayoutCell()
bulk_group = bulk_layout.makeCellGroup("bulk")
bulk_layout.nodeGraph = {"VSS": type("Node", (), {"ports": []})()}
bulk_layout.nodeGraphList = ["VSS"]
for idx in range(2):
    inst = add_instance(bulk_layout, f"xn_bulk{idx}")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
    bulk_layout.nodeGraph["VSS"].ports.append(port_stub(inst, "S"))
    bulk_layout.nodeGraph["VSS"].ports.append(port_stub(inst, "B"))
    bulk_group.addStack(f"bulk{idx}", [inst]).stack()
bulk_outside = add_instance(bulk_layout, "xbulk_out")
bulk_outside.getTerminalAccess = lambda terminal, target_layer="M2": TerminalAccess(terminal, target_layer, target_layer, None, [], [Rect(target_layer, 200, 0, 10, 10)])
bulk_layout.nodeGraph["VSS"].ports.append(port_stub(bulk_outside, "S"))
default_bulk_ports = bulk_group.exportBoundaryPorts(layer="M2")
assert len(default_bulk_ports) == 1
assert default_bulk_ports[0].x1 == 60
assert bulk_group.exportBoundaryPorts(layer="M2", options="bulk")[0].x1 == 80
assert bulk_group.exportBoundaryPorts(layer="M2", options="terminal=B")[0].x1 == 80
bulk_top_rects = bulk_layout.getNodeAccessRects("VSS", "M2")
assert any(r.x1 == 60 for r in bulk_top_rects)
assert not any(r.x1 == 80 for r in bulk_top_rects)

transistor_layout = LayoutCell()
for idx in range(2):
    inst = add_instance(transistor_layout, f"xn_t1<{idx}>")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
transistor_layout.nodeGraph = {"VT": type("Node", (), {"ports": []})()}
for inst in transistor_layout.children:
    transistor_layout.nodeGraph["VT"].ports.append(port_stub(inst, "G"))

transistor_group = transistor_layout.makeCellGroup("nmos")
transistor_stack = transistor_group.transistorStack("xn_t")
assert len(transistor_stack.parallel_groups) == 1
assert "VT" in transistor_stack.parallel_groups[0].group_ports

diode_layout = LayoutCell()
diode_inst = add_instance(diode_layout, "xn_diode1")
diode_inst.getTerminalAccess = lambda terminal, target_layer="M1": access(target_layer, terminal, 0)
diode_layout.nodeGraph = {"VDIO": type("Node", (), {"ports": []})()}
diode_layout.nodeGraph["VDIO"].ports.append(port_stub(diode_inst, "D"))
diode_layout.nodeGraph["VDIO"].ports.append(port_stub(diode_inst, "G"))

diode_group = diode_layout.makeCellGroup("nmos")
diode_stack = diode_group.transistorStack("xn_diode")
assert len(diode_stack.diode_routes) == 1
assert diode_stack.diode_routes[0].layer == "M1"
assert diode_stack.diode_routes[0].net == "VDIO"
assert diode_stack.diode_routes[0] in diode_stack.children
assert diode_stack.diode_routes[0] not in diode_layout.children

mirror_layout = LayoutCell()
mirror_insts = []
for idx in range(3):
    inst = add_instance(mirror_layout, f"xp_mirr{idx + 1}")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
    mirror_insts.append(inst)
mirror_outside = add_instance(mirror_layout, "xbias")
mirror_outside.moveTo(200, 500)
mirror_outside.getTerminalAccess = lambda terminal, target_layer="M2": TerminalAccess(terminal, target_layer, target_layer, None, [], [Rect(target_layer, 200, 500, 10, 10)])
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
