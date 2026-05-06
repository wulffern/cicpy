"""Test the C++-compatible path semantics of Cell.findAllRectangles.

Mirrors the contract of cIcCore::Cell::findAllRectangles from
ciccreator/cic-core/src/core/cell.cpp. Required for §7 Steps 3-5 to use
addDirectedRoute with `instname:terminal` route strings.
"""

from cicpy.core.cell import Cell
from cicpy.core.instance import Instance
from cicpy.core.rect import Rect
from cicpy.core.port import Port


def make_port(name, layer, x=0, y=0):
    return Port(name, routeLayer=layer, rect=Rect(layer, x, y, 10, 10))


# ---- 1. instname:port resolves into the instance's local port ----------------
parent = Cell("parent")
child = Instance()
child.instanceName = "MP"
child.name = "NCH"
child.add(make_port("D", "M1", x=10, y=20))
child.add(make_port("G", "M1", x=30, y=20))
parent.add(child)

rects = parent.findAllRectangles("MP:D", "M1")
assert len(rects) == 1, f"MP:D should resolve to 1 rect, got {len(rects)}"
assert rects[0].x1 == 10 and rects[0].y1 == 20
assert rects[0].layer == "M1"

# ---- 2. Comma-split unions matches -------------------------------------------
rects = parent.findAllRectangles("MP:D,MP:G", "M1")
assert len(rects) == 2, f"MP:D,MP:G should return 2 rects, got {len(rects)}"
assert {r.x1 for r in rects} == {10, 30}

# ---- 3. Layer filter — wrong layer drops the rect ----------------------------
rects = parent.findAllRectangles("MP:D", "M2")
assert len(rects) == 0, "M2 request should not return an M1 port rect"

# ---- 4. Instance regex doesn't match ----------------------------------------
rects = parent.findAllRectangles("XX:D", "M1")
assert len(rects) == 0

# ---- 5. Regex (not exact) match on instance name ----------------------------
# `M.` should match instance name "MP".
rects = parent.findAllRectangles("M.:D", "M1")
assert len(rects) == 1
assert rects[0].x1 == 10

# ---- 6. named_rects bare-name lookup ----------------------------------------
parent.named_rects["rail_VDD"] = Rect("M1", 100, 100, 200, 5)
rects = parent.findAllRectangles("rail_VDD", "M1")
assert any(getattr(r, "x1", None) == 100 for r in rects), "rail_VDD should be found in named_rects"

# ---- 7. Nested instname:subinst:port recurses through instance hierarchy ----
# Build parent → outer instance "OUT" → inner instance "MIN" → port "D".
parent2 = Cell("parent2")
outer = Instance()
outer.instanceName = "OUT"
outer.name = "OUTCELL"
inner = Instance()
inner.instanceName = "MIN"
inner.name = "INCELL"
inner.add(make_port("D", "M1", x=42, y=7))
outer.add(inner)
parent2.add(outer)

rects = parent2.findAllRectangles("OUT:MIN:D", "M1")
assert len(rects) == 1, f"OUT:MIN:D should recurse two levels, got {len(rects)}"
assert rects[0].x1 == 42 and rects[0].y1 == 7

# ---- 8. Empty / whitespace segments are tolerated ---------------------------
rects = parent.findAllRectangles("MP:D, ,MP:G", "M1")
assert len(rects) == 2, "blank comma segment should be ignored"

with open("findrects.status", "w") as fh:
    fh.write("findrects test passed\n")
