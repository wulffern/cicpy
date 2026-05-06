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
assert [i.instanceName for i in stack.instances] == [
    "xn_a1",
    "xn_a2<0>",
    "xn_a2<1>",
    "xn_a2<3>",
    "xn_a10",
    "xfill_xn_a1<0>",
]
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

parallel_layout.nodeGraph = {
    "VPAR": type("Node", (), {"ports": []})(),
    "VSER": type("Node", (), {"ports": []})(),
    "VSS": type("Node", (), {"ports": []})(),
}
for inst in parallel_insts:
    parallel_layout.nodeGraph["VPAR"].ports.append(type("Port", (), {"parent": inst, "childName": "D"})())
    parallel_layout.nodeGraph["VSS"].ports.append(type("Port", (), {"parent": inst, "childName": "S"})())
for inst in parallel_insts[:2]:
    parallel_layout.nodeGraph["VSER"].ports.append(type("Port", (), {"parent": inst, "childName": "D"})())

parallel_group = parallel_layout.makeCellGroup("pmos")
parallel_stack = parallel_group.addParallelStack("par", parallel_insts).stack().routeParallel()
assert len(parallel_stack.parallel_groups) == 1
parallel_bus = parallel_stack.parallel_groups[0]
assert "VPAR" in parallel_bus.group_ports
assert "VSER" not in parallel_bus.group_ports
assert "VSS" in parallel_bus.group_ports
assert len(parallel_bus.route_rects) == 2
assert parallel_bus.route_rects[0] in parallel_bus.children
assert parallel_bus.route_rects[0] in parallel_layout.children
assert parallel_bus.route_rects[0].width() == 10
assert parallel_bus.route_rects[0].height() == 210

transistor_layout = LayoutCell()
for idx in range(2):
    inst = add_instance(transistor_layout, f"xn_t1<{idx}>")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
transistor_layout.nodeGraph = {"VT": type("Node", (), {"ports": []})()}
for inst in transistor_layout.children:
    transistor_layout.nodeGraph["VT"].ports.append(type("Port", (), {"parent": inst, "childName": "G"})())

transistor_group = transistor_layout.makeCellGroup("nmos")
transistor_stack = transistor_group.transistorStack("xn_t")
assert len(transistor_stack.parallel_groups) == 1
assert "VT" in transistor_stack.parallel_groups[0].group_ports

diode_layout = LayoutCell()
diode_inst = add_instance(diode_layout, "xn_diode1")
diode_inst.getTerminalAccess = lambda terminal, target_layer="M1": access(target_layer, terminal, 0)
diode_layout.nodeGraph = {"VDIO": type("Node", (), {"ports": []})()}
diode_layout.nodeGraph["VDIO"].ports.append(type("Port", (), {"parent": diode_inst, "childName": "D"})())
diode_layout.nodeGraph["VDIO"].ports.append(type("Port", (), {"parent": diode_inst, "childName": "G"})())

diode_group = diode_layout.makeCellGroup("nmos")
diode_stack = diode_group.transistorStack("xn_diode")
assert len(diode_stack.diode_routes) == 1
assert diode_stack.diode_routes[0].layer == "M1"
assert diode_stack.diode_routes[0].net == "VDIO"
assert diode_stack.diode_routes[0] in diode_stack.children
assert diode_stack.diode_routes[0] in diode_layout.children

mirror_layout = LayoutCell()
mirror_insts = []
for idx in range(3):
    inst = add_instance(mirror_layout, f"xp_mirr{idx + 1}")
    inst.moveTo(0, idx * 100)
    inst.getTerminalAccess = lambda terminal, target_layer="M2", idx=idx: access(target_layer, terminal, idx * 100)
    mirror_insts.append(inst)
mirror_layout.nodeGraph = {
    "VG": type("Node", (), {"ports": []})(),
    "VS": type("Node", (), {"ports": []})(),
    "VD0": type("Node", (), {"ports": []})(),
    "VD1": type("Node", (), {"ports": []})(),
    "VD2": type("Node", (), {"ports": []})(),
}
for idx, inst in enumerate(mirror_insts):
    mirror_layout.nodeGraph["VG"].ports.append(type("Port", (), {"parent": inst, "childName": "G"})())
    mirror_layout.nodeGraph["VS"].ports.append(type("Port", (), {"parent": inst, "childName": "S"})())
    mirror_layout.nodeGraph[f"VD{idx}"].ports.append(type("Port", (), {"parent": inst, "childName": "D"})())

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
