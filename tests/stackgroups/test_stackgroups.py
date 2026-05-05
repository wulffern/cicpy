from cicpy.core.instance import Instance
from cicpy.core.layoutcell import LayoutCell


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

with open("stackgroups.status", "w", encoding="utf-8") as fh:
    fh.write("stack group helper test passed\n")
