"""A track router: find a path for a net through what is already drawn.

Why this exists
---------------

The route language says *where* a wire goes: a layer, a shape, a track
number. That works while the cell is empty and stops working when it is
not. Every failure in a crowded cell has the same form -- the trunk
lands on another net's trunk, the bar crosses another net's bar -- and
no track number fixes it, because the corridor is occupied rather than
mis-numbered. Tuning a track by hand is solving a bin packing problem
one regeneration at a time.

So: read what is already drawn, and search for a path that is free.

What it borrows from magic
--------------------------

magic's maze router (mzrouter/) expands a partial path to the next
*interesting point* in each direction plus vias to neighbouring layers,
and picks the partial path with the lowest estimated total cost. Two
ideas are taken from it:

- The cost model. magic's tech file gives every route layer an ``hcost``
  and a ``vcost`` per unit distance, plus a ``jogcost``, and every
  contact a cost of its own. A layer that prefers to run vertically is
  expressed as a cheap vcost and an expensive hcost, not as a rule that
  forbids horizontal. Preference, not prohibition, is what lets a router
  break its own convention when that is the only way through.
- Estimated total cost, so the search is A* rather than breadth first:
  the estimate is the Manhattan distance to the goal times the cheapest
  rate available, which never overestimates and so keeps A* admissible.

What it does not borrow: magic's windowed search, blooming, and the
tile-plane geometry that finds interesting points in constant time. This
router walks a coarse track grid instead, which is enough for a cell
with tens of nets and is far less code to be wrong in.

The grid
--------

Tracks come from the routing pitch, one line every ``ROUTE`` grid step,
so a path lands where the rest of the flow already puts wires. A node is
(track_x, track_y, layer). Edges are a step to the neighbouring track on
the same layer, cost = distance times that layer's rate for the
direction, and a via to the layer above or below at that layer pair's
cost. A node is blocked when a rect of a *different* net overlaps the
wire that would be drawn there, plus the design rule spacing for the
layer.
"""

import heapq
import logging
import re
from collections import defaultdict

from .cut import Cut
from .rect import Rect
from .rules import Rules


class RouteLayer:
    """One routable layer and what it costs to travel on.

    hcost and vcost are per unit distance, following magic's mzrouter
    tech syntax. A layer meant for vertical wires carries a low vcost
    and a high hcost.
    """

    def __init__(self, name, hcost=1, vcost=1, width=None, space=None):
        self.name = name
        self.hcost = hcost
        self.vcost = vcost
        self.width = width
        self.space = space

    def rate(self, horizontal):
        return self.hcost if horizontal else self.vcost

    def __repr__(self):
        return f"RouteLayer({self.name}, h={self.hcost}, v={self.vcost})"


#- The house convention, written as costs rather than rules: M2 and M4
#- want to run vertically, M3 horizontally, and M1 is the pins' own
#- layer so it is expensive in both directions and used only to reach
#- them. A router may still break the convention where it must, it just
#- pays for it.
DEFAULT_LAYER_COSTS = {
    #- M1 is the pins' own layer and belongs to power. The router has to
    #- be able to *start* there, since that is where a pin is, but must
    #- not travel along it, so it is priced out rather than removed
    "M1": (200, 200),
    "M2": (8, 1),
    "M3": (1, 8),
    "M4": (8, 1),
}

#- A via costs this many track pitches. Costs elsewhere are per unit
#- distance and get multiplied by the pitch, so a bare number here would
#- make vias free next to any step at all and the search would stagger
#- up and down the stack instead of going around.
DEFAULT_VIA_PITCHES = 3


class TrackRouter:
    """Route one net at a time over a track grid, avoiding what is drawn.

    Usage from a pycell hook::

        r = TrackRouter(layout)
        r.route("VO")

    ``route`` returns the Route it added, or None when it cannot find a
    path, and says why in the log rather than drawing something wrong.
    """

    def __init__(self, layout, layers=None, via_cost=None,
                 pitch=None):
        self.log = logging.getLogger("TrackRouter")
        self.layout = layout
        self.rules = Rules.getInstance()

        self.layers = []
        for name, (hc, vc) in (layers or DEFAULT_LAYER_COSTS).items():
            width = space = None
            try:
                width = self.rules.get(name, "width")
                space = self.rules.get(name, "space")
            except Exception:
                pass
            self.layers.append(RouteLayer(name, hc, vc, width, space))
        self.layer_index = {l.name: i for i, l in enumerate(self.layers)}

        if pitch is None:
            try:
                pitch = self.rules.get("ROUTE", "horizontalgrid")
            except Exception:
                pitch = 1000
        self.pitch = int(pitch)
        self.via_cost = via_cost if via_cost is not None \
            else DEFAULT_VIA_PITCHES * self.pitch

        #- layers a path may touch but not run along
        self.no_travel = {"M1"}

        self._obstacles = None
        self._bounds = None

    #-----------------------------------------------------------------
    #- The picture of what is already there
    #-----------------------------------------------------------------

    def _collect(self):
        """Index every drawn rect by layer, with the net that owns it."""
        obstacles = defaultdict(list)
        rects = self.layout._collectPhysicalRects()
        for r in rects:
            layer = getattr(r, "layer", "")
            if layer in self.layer_index:
                obstacles[layer].append(r)
        self._obstacles = obstacles

        x1 = min((r.x1 for rs in obstacles.values() for r in rs), default=0)
        y1 = min((r.y1 for rs in obstacles.values() for r in rs), default=0)
        x2 = max((r.x2 for rs in obstacles.values() for r in rs), default=0)
        y2 = max((r.y2 for rs in obstacles.values() for r in rs), default=0)
        self._bounds = (x1, y1, x2, y2)
        self.log.debug(
            f"track grid over ({x1},{y1})-({x2},{y2}) pitch {self.pitch}, "
            f"{sum(len(v) for v in obstacles.values())} rects")

    def _via_box(self, node, la, lb):
        """The footprint of the real cut cell, not a nominal square.

        A cut is a cell: enclosures on both metals and the via array
        between them, and for M1M2 2x1 in sky130 that is 9200 by 3400
        database units. Checking a pitch sized square instead let vias
        land on other nets while every step looked clear.
        """
        try:
            cut = Cut.getInstance(la, lb, 1, 1)
        except Exception:
            cut = None
        tx, ty, _ = node
        x, y = tx * self.pitch, ty * self.pitch
        if cut is None:
            w = h = self.pitch
        else:
            w, h = cut.width(), cut.height()
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)

    def _via_blocked(self, node, la, lb, net):
        """Is the cut's footprint free on the layer it is entering?

        Only the destination layer is checked. The cut's enclosure on
        the layer being left is by definition sitting on this net's own
        wire or pin, and a pin here is 4 um tall while the enclosure is
        taller, so demanding the enclosure clear every neighbouring pin
        made two of three pins on a real net unreachable: the search
        could not leave them at all.
        """
        box = self._via_box(node, la, lb)
        return self._blocked(lb, box, net, margin=0)

    def _blocked(self, layer, box, net, margin=None):
        """Is this box free of everything that is not our own net?

        margin is the clearance demanded around the box. It defaults to
        the layer's own spacing rule; a via passes 0 because the cut
        cell already carries its enclosures and asking for metal spacing
        on top of them rejects every entry in a field of pins.
        """
        space = 0
        if margin is not None:
            space = margin
        else:
            for l in self.layers:
                if l.name == layer and l.space:
                    space = l.space
        bx1, by1, bx2, by2 = box
        for r in self._obstacles.get(layer, ()):
            if getattr(r, "net", "") == net:
                continue
            if (r.x1 - space < bx2 and r.x2 + space > bx1 and
                    r.y1 - space < by2 and r.y2 + space > by1):
                return True
        return False

    #-----------------------------------------------------------------
    #- The search
    #-----------------------------------------------------------------

    def _nodes_for_rect(self, rect, layer_name):
        """Track nodes a pin rectangle can be entered from."""
        out = []
        li = self.layer_index.get(layer_name)
        if li is None:
            return out
        for tx in range(int(rect.x1 // self.pitch), int(rect.x2 // self.pitch) + 1):
            for ty in range(int(rect.y1 // self.pitch), int(rect.y2 // self.pitch) + 1):
                out.append((tx, ty, li))
        return out

    def _wire_box(self, node, direction):
        """The rectangle a step from this node would draw."""
        tx, ty, li = node
        layer = self.layers[li]
        w = layer.width or self.pitch // 2
        x = tx * self.pitch
        y = ty * self.pitch
        if direction in ("e", "w"):
            return (x - self.pitch, y - w // 2, x + self.pitch, y + w // 2)
        return (x - w // 2, y - self.pitch, x + w // 2, y + self.pitch)

    def _neighbours(self, node, net):
        tx, ty, li = node
        layer = self.layers[li]
        #- A pin sits on M1 and the search has to be able to stand there,
        #- but M1 belongs to power and the pins themselves: no travelling
        #- along it, only up. Pricing it high was not enough, the first
        #- step off a pin is unavoidable and the search took it
        if layer.name in self.no_travel:
            for dli in (li - 1, li + 1):
                if 0 <= dli < len(self.layers):
                    other = self.layers[dli]
                    if not self._via_blocked(node, layer.name, other.name, net):
                        yield (tx, ty, dli), self.via_cost
            return
        for dx, dy, direction, horizontal in (
                (1, 0, "e", True), (-1, 0, "w", True),
                (0, 1, "n", False), (0, -1, "s", False)):
            nxt = (tx + dx, ty + dy, li)
            box = self._wire_box(node, direction)
            if self._blocked(layer.name, box, net):
                continue
            yield nxt, layer.rate(horizontal) * self.pitch

        for dli in (li - 1, li + 1):
            if not (0 <= dli < len(self.layers)):
                continue
            other = self.layers[dli]
            if self._via_blocked(node, layer.name, other.name, net):
                continue
            yield (tx, ty, dli), self.via_cost

    def _estimate(self, node, goals):
        """Manhattan distance to the nearest goal, at the cheapest rate.

        Never an overestimate, which is what keeps A* honest.
        """
        cheapest = min(min(l.hcost, l.vcost) for l in self.layers)
        tx, ty, _ = node
        best = None
        for gx, gy, _ in goals:
            d = (abs(gx - tx) + abs(gy - ty)) * self.pitch * cheapest
            if best is None or d < best:
                best = d
        return best or 0

    def search(self, starts, goals, net, max_nodes=200000):
        """A* from any start node to any goal node. Returns the path."""
        goal_set = set(goals)
        frontier = []
        for s in starts:
            heapq.heappush(frontier, (self._estimate(s, goals), 0, s, None))
        came = {}
        best = {}
        expanded = 0

        while frontier:
            _, cost, node, parent = heapq.heappop(frontier)
            if node in came:
                continue
            came[node] = parent
            if node in goal_set:
                path = []
                while node is not None:
                    path.append(node)
                    node = came[node]
                path.reverse()
                self.log.debug(f"{net}: path of {len(path)} nodes, "
                               f"{expanded} expanded, cost {cost}")
                return path
            expanded += 1
            if expanded > max_nodes:
                self.log.warning(
                    f"{net}: gave up after {expanded} nodes")
                return None
            for nxt, step in self._neighbours(node, net):
                if nxt in came:
                    continue
                ncost = cost + step
                if nxt in best and best[nxt] <= ncost:
                    continue
                best[nxt] = ncost
                heapq.heappush(
                    frontier,
                    (ncost + self._estimate(nxt, goals), ncost, nxt, node))
        return None

    #-----------------------------------------------------------------
    #- Turning a path into geometry
    #-----------------------------------------------------------------

    def validate_vias(self, vias, net):
        for a, b in vias:
            la = self.layers[a[2]].name
            lb = self.layers[b[2]].name
            if self._via_blocked(a, la, lb, net):
                self.log.warning(
                    f"{net}: path rejected, {la}/{lb} via at "
                    f"({a[0] * self.pitch},{a[1] * self.pitch}) is not free")
                return False
        return True

    def validate(self, rects, net):
        """Would any of this geometry touch another net?

        The search avoids obstacles a step at a time; this checks the
        wire that actually comes out. A router that cannot find a path
        is an inconvenience, a router that draws a short is a bug, so
        when these disagree the geometry is thrown away.
        """
        for r in rects:
            box = (r.x1, r.y1, r.x2, r.y2)
            if self._blocked(r.layer, box, net):
                self.log.warning(
                    f"{net}: path rejected, {r.layer} "
                    f"({r.x1},{r.y1})-({r.x2},{r.y2}) is not free")
                return False
        return True

    def _path_to_rects(self, path, net):
        """Collapse a node path into one rect per straight run, plus vias."""
        rects = []
        vias = []
        run = [path[0]]
        for node in path[1:]:
            if node[2] != run[-1][2]:
                rects.extend(self._run_to_rects(run, net))
                vias.append((run[-1], node))
                run = [node]
            else:
                run.append(node)
        rects.extend(self._run_to_rects(run, net))
        return rects, vias

    def _run_to_rects(self, run, net):
        if len(run) < 2:
            return []
        layer = self.layers[run[0][2]]
        w = layer.width or self.pitch // 2
        out = []
        seg = [run[0]]
        for node in run[1:]:
            horizontal = node[1] == seg[-1][1]
            prev_horizontal = (len(seg) < 2) or (seg[-1][1] == seg[-2][1])
            if len(seg) >= 2 and horizontal != prev_horizontal:
                out.append(self._segment(seg, layer, w, net))
                seg = [seg[-1]]
            seg.append(node)
        if len(seg) >= 2:
            out.append(self._segment(seg, layer, w, net))
        return [r for r in out if r is not None]

    def _segment(self, seg, layer, w, net):
        xs = [n[0] * self.pitch for n in seg]
        ys = [n[1] * self.pitch for n in seg]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        if x1 == x2:
            r = Rect(layer.name, x1 - w // 2, y1, w, y2 - y1)
        else:
            r = Rect(layer.name, x1, y1 - w // 2, x2 - x1, w)
        r.net = net
        return r
