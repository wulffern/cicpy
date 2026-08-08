######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2026-8-8
## ###################################################################
"""A scoped shortest-path router over the track grid.

Independent of ``route.py``. Nothing here draws geometry yet: this is
the search and the cost model, which is the part the old router does not
have. It answers "where should this net go", and it answers it against
obstacles that include *other nets' pins* -- the thing every routing
failure in LELOTEMP_OTAR turned out to be.

The grid is (track_x, track_y, layer). Moves are a step along a layer's
preferred direction, or a via to an adjacent layer. Dijkstra rather than
A* to begin with: correctness first, and these grids are small enough
that the heuristic buys little. ``search`` takes an optional heuristic
so A* is a one-argument change once the costs are trusted.

See plans/router_plan.md.
"""
import heapq
import logging
import re

from .rules import Rules
from collections import defaultdict


class Blocked(Exception):
    """No path exists. Carries why, because 'no route' is not a diagnosis."""

    def __init__(self, message, reached=0, blockers=None):
        super().__init__(message)
        self.reached = reached
        self.blockers = blockers or []


class MazeRouter:
    """Shortest path for one net, over one scope.

    Costs are in database units so that length and via cost are directly
    comparable, which is what lets the search trade a detour against a
    via instead of having the preference hard coded.
    """

    #- A via is not a point, and its size comes from the technology, not
    #- from here. Asking Cut for it was the fix for a bad guess: 8800
    #- was carried over from a note about pad clashes and the real 1x1
    #- cut is 4000 square. At 8800 the router could not leave a pin at
    #- all in the switch column, where pins are 4000 apart -- it
    #- reported every ladder net blocked, which was its own constant
    #- talking rather than the layout.
    #- No layer names and no sizes here. The technology carries them:
    #-   ROUTE.pinlayer     which layer is pin-only
    #-   ROUTE.directions   which way each routing layer runs
    #-   layer previous/next   the stack order and via adjacency
    #-   <layer> width/space   the legal wire pitch
    #-   Cut.getInstance       the real via size
    #- A router that hard codes any of these is a router for one PDK.

    def __init__(self, trackmap, net, via_cost=None, log=None):
        self.tm = trackmap
        self.net = net
        #- default: a via costs what it physically occupies. Not a tuned
        #- constant -- if a detour is shorter than the pad it displaces,
        #- the detour genuinely is cheaper.
        self._via_size = {}
        self._clearance = {}
        self.log = log or logging.getLogger("MazeRouter")
        #- stack order from the technology's own chain, filtered to the
        #- layers this map actually has tracks for
        stack = [l for l in self.tm.metal_stack() if l in self.tm.directions]
        self._layers = stack or sorted(self.tm.directions)
        self.pin_only = tuple(l for l in (self.tm.pin_layer,) if l)
        self.via_cost = (self._default_via_cost()
                         if via_cost is None else via_cost)
        self._adj = self._layer_adjacency()
        self._pin_index = self._index_foreign_pins()
        #- rects this route may land on; set by connect()
        self._own = []

    #-----------------------------------------------------------------
    #- the grid
    #-----------------------------------------------------------------

    def _default_via_cost(self):
        """A via costs what it physically occupies, from the technology."""
        routing = [l for l in self._layers if l not in self.pin_only]
        if len(routing) >= 2:
            return self.via_extent(routing[0], routing[1])[0]
        if len(self._layers) >= 2:
            return self.via_extent(self._layers[0], self._layers[1])[0]
        return self.rule(self._layers[0] if self._layers else "", "width")

    def _layer_adjacency(self):
        """Which layers a via may connect.

        Neighbours in the stack, and the stack comes from the tech
        file's previous/next chain, not from sorting names -- sorting
        happened to work for M1..M5 and puts M10 between M1 and M2 the
        moment a technology has one.
        """
        adj = defaultdict(list)
        for a, b in zip(self._layers, self._layers[1:]):
            adj[a].append(b)
            adj[b].append(a)
        return adj

    #- Bucket size for the pin index. Coarse on purpose: it only has to
    #- cut the candidate set down, and an exact overlap test runs after.
    BUCKET = 20000

    def _index_foreign_pins(self):
        """Every pin not belonging to this net, bucketed by position.

        `column_blockers` walks every track on every layer, which is
        fine for a question asked once and ruinous for one asked per
        node expansion: the first search over LELOTEMP_OTAR did not
        finish in five minutes. The obstacles do not change during a
        search, so they are gathered once here.

        Buckets are keyed on the axis the pin's own layer runs along.
        """
        #- a set: one pin spans many tracks and would otherwise be
        #- indexed once per track. Measured, 45 copies of a single box.
        index = defaultdict(set)
        for layer, direction in self.tm.directions.items():
            horizontal = direction == "h"
            for t in self.tm.tracks.get(layer, []):
                for other, spans in t.pins.items():
                    if other == self.net:
                        continue
                    for s0, s1 in spans:
                        #- (x1, x2, y1, y2) of the pin, whichever way
                        #- its layer runs
                        box = ((s0, s1, t.coord, t.coord) if horizontal
                               else (t.coord, t.coord, s0, s1))
                        lo = int(min(box[0], box[2]) // self.BUCKET)
                        hi = int(max(box[1], box[3]) // self.BUCKET)
                        for b in range(lo, hi + 1):
                            index[b].add((other, box))
        return {k: list(v) for k, v in index.items()}

    def _pins_near(self, x1, x2, y1, y2):
        lo = int(min(x1, y1) // self.BUCKET)
        hi = int(max(x2, y2) // self.BUCKET)
        out = []
        for b in range(lo, hi + 1):
            out.extend(self._pin_index.get(b, ()))
        return out

    def _coords(self, layer):
        return [t.coord for t in self.tm.tracks.get(layer, [])]

    def rule(self, layer, name, default=None):
        """A numeric design rule. Raises rather than inventing a number:
        a silently defaulted spacing is a short waiting to happen."""
        try:
            from cicpy.core.rules import Rules
            return int(Rules.getInstance().get(layer, name))
        except Exception:
            if default is None:
                raise
            return default

    def clearance(self, layer):
        """How far a foreign wire must be from this one's centreline.

        width + space, which is the wire pitch the technology actually
        allows. THE TRACK GRID IS FINER THAN THAT. In sky130 here the
        metal is 3000 wide and wants 3000 of space, so wires must sit
        6000 apart -- while TrackMap cuts tracks every 3000. Two nets on
        ADJACENT tracks abut exactly and short.

        That is what shorted VD2 into VS: the route was legal on its own
        track, which is all is_free used to check, and touched the
        neighbour's.
        """
        if layer not in self._clearance:
            self._clearance[layer] = (self.rule(layer, "width")
                                      + self.rule(layer, "space"))
        return self._clearance[layer]

    def is_free(self, layer, coord, lo, hi):
        """Can this net occupy `layer` at `coord`, from lo..hi?

        Checks the track AND every track within one clearance of it,
        because a wire is wider than a track pitch. Takes the coordinate
        rather than a Track so the neighbours can be found at all.
        """
        tracks = self.tm.tracks.get(layer)
        if not tracks:
            return False
        reach = self.clearance(layer)
        near = False
        for t in tracks:
            if abs(t.coord - coord) >= reach:
                continue
            near = True
            if t.wire_overlaps(self.net, lo, hi):
                return False
            if t.crosses_pin(self.net, lo, hi):
                return False
        return near

    def _via_layers(self, a_layer, b_layer):
        """The layers a via between a_layer and b_layer occupies."""
        try:
            i, j = self._layers.index(a_layer), self._layers.index(b_layer)
        except ValueError:
            return dict(self.tm.directions)
        lo, hi = sorted((i, j))
        return {l: self.tm.directions[l] for l in self._layers[lo:hi + 1]
                if l in self.tm.directions}

    def via_enclosure(self, layer, a_layer, b_layer):
        """How far `layer` must extend past the cut joining a and b.

        The cut layer sits between the two metals in the technology's
        own chain, so its name comes from there rather than from a
        table: M3.next is VIA3 when M4 is above it.
        """
        names = []
        for l in (a_layer, b_layer):
            try:
                lay = Rules.getInstance().getLayer(l)
            except Exception:
                continue
            for attr in ("next", "previous"):
                v = getattr(lay, attr, "")
                if v:
                    names.append(v)
        for v in names:
            try:
                return int(Rules.getInstance().get(layer, v + "enclosure"))
            except Exception:
                continue
        return 0

    def via_extent(self, a_layer, b_layer):
        """(width, height) of the real cut between two layers."""
        key = tuple(sorted((a_layer, b_layer)))
        if key not in self._via_size:
            try:
                from cicpy.core.cut import Cut
                inst = Cut.getInstance(a_layer, b_layer, 1, 1)
                self._via_size[key] = (int(inst.width()), int(inst.height()))
            except Exception:
                #- no cut between these layers; fall back to the wire
                #- width, which the technology does define
                w = self.rule(a_layer, "width")
                self._via_size[key] = (w, w)
        return self._via_size[key]

    def own_metal(self, x1, x2, y1, y2):
        """Does this box overlap metal the route is allowed to land on?

        The pin rects it was asked to join. Unattributed metal on the pin
        layer is otherwise indistinguishable from a device's internal
        rail -- `_collectPhysicalRects` can only attribute PORTS -- so
        without this the choice is between allowing a via anywhere on the
        pin layer (which drops pads within 0.17 of a device rail, 14
        li.3 errors measured) and allowing none at all (which blocks
        every via off every pin, by the pin itself).

        The route knows the answer and was throwing it away: connect()
        is handed the two rects it is joining.
        """
        for r in self._own:
            if r is None:
                continue
            if not (x2 <= r.x1 or x1 >= r.x2) and not (y2 <= r.y1 or y1 >= r.y2):
                return True
        return False

    def via_is_free(self, x, y, a_layer=None, b_layer=None):
        """Can this net drop a via column at (x, y)?

        The column is the cut's real size and claims every layer, so this is
        where two nets most often collide -- and it is exactly what
        `column_blockers` was built to answer.
        """
        routing = [l for l in self._layers if l not in self.pin_only]
        d0 = routing[0] if routing else (self._layers[0] if self._layers else "")
        d1 = routing[1] if len(routing) > 1 else d0
        w, h = self.via_extent(a_layer or d0, b_layer or d1)
        hw, hh = w // 2, h // 2
        ax1, ax2, ay1, ay2 = x - hw, x + hw, y - hh, y + hh
        for _net, (bx1, bx2, by1, by2) in self._pins_near(ax1, ax2, ay1, ay2):
            if not (ax2 <= bx1 or ax1 >= bx2) and not (ay2 <= by1 or ay1 >= by2):
                return False
        #- and other nets' WIRE, not only their pins. Checking pins alone
        #- was not enough: routing five ladder nets in one column landed
        #- a via of one on the metal of another and shorted them, with
        #- the report blaming no route at all because the geometry came
        #- from the emitter rather than route.py.
        #-
        #- But only the layers this via actually CONNECTS. An earlier
        #- version scanned every layer in the column, on the reasoning
        #- that a route reaching a pin comes down through all of them --
        #- true of a whole descent, false of one step. It made an M1->M2
        #- via illegal underneath an unrelated M4 wire, which is not a
        #- short in any technology, and it blocked every ladder net at
        #- its own pin.
        for layer, direction in self._via_layers(a_layer, b_layer).items():
            horizontal = direction == "h"
            lo, hi = (ay1, ay2) if horizontal else (ax1, ax2)
            a, b = (ax1, ax2) if horizontal else (ay1, ay2)
            #- A pad needs SPACE from a neighbour, not merely to miss
            #- it. Checking only tracks whose coordinate is inside the
            #- pad lets a wire one track away sit hard against it: the
            #- pad reaches 2000 from centre and a wire on the next track
            #- starts at 1500, so they overlap outright, and even clear
            #- of that they must still be `space` apart.
            margin = (self.rule(layer, "space")
                      + self.rule(layer, "width") // 2)
            for t in self.tm.tracks.get(layer, []):
                if not (lo - margin <= t.coord <= hi + margin):
                    continue
                #- On the pin layer, look at unattributed metal too and
                #- let the route's own pins through. Everywhere else the
                #- layer rule stands.
                strict = layer in self.pin_only
                for _other, s0, s1 in t.foreign_spans(
                        self.net, a, b,
                        tolerate_unattributed=(not strict)):
                    if strict and self.own_metal(ax1, ax2, ay1, ay2):
                        continue
                    return False
        return True

    #-----------------------------------------------------------------
    #- the search
    #-----------------------------------------------------------------

    def snap(self, node):
        """Nearest grid node to (x, y, layer).

        A caller gives pin coordinates, which are wherever the cell put
        them, and the grid only has points at the routing pitch. Without
        snapping a goal one pitch off the grid is simply unreachable and
        the search reports it as blocked -- measured, a goal 1000 units
        off a 3000 pitch came back "no path, closest approach 1000
        away", which is true and useless.
        """
        x, y, layer = node
        horizontal = self.tm.directions.get(layer) == "h"
        along = self.tm.hpitch if horizontal else self.tm.vpitch
        x1, y1, _, _ = self.tm.extent
        if horizontal:
            base = x1
            x = base + round((x - base) / along) * along
            t = self.tm.track_at(layer, y)
            y = t.coord if t is not None else y
        else:
            base = y1
            y = base + round((y - base) / along) * along
            t = self.tm.track_at(layer, x)
            x = t.coord if t is not None else x
        return (int(x), int(y), layer)

    def search(self, start, goal, heuristic=None):
        """Dijkstra (or A*, given a heuristic) from start to goal.

        `start` and `goal` are (x, y, layer). Returns the path as a list
        of those, cheapest first. Raises `Blocked` with how far it got
        and what stopped it, because a router that says only "no" cannot
        be debugged.
        """
        start, goal = self.snap(start), self.snap(goal)
        h = heuristic or (lambda n: 0)
        dist = {start: 0}
        prev = {}
        seen = set()
        pq = [(h(start), 0, start)]
        best = start
        best_d = float("inf")

        while pq:
            _, d, node = heapq.heappop(pq)
            if node in seen:
                continue
            seen.add(node)
            if node == goal:
                return self._unwind(prev, node)
            gd = self._manhattan(node, goal)
            if gd < best_d:
                best_d, best = gd, node
            for nxt, step in self.neighbours(node):
                if nxt in seen:
                    continue
                nd = d + step
                if nd < dist.get(nxt, float("inf")):
                    dist[nxt] = nd
                    prev[nxt] = node
                    heapq.heappush(pq, (nd + h(nxt), nd, nxt))

        raise Blocked(
            f"no path for {self.net} from {start} to {goal}; "
            f"closest approach {best} ({best_d} away)",
            reached=len(seen),
            blockers=self.tm.column_blockers(
                self.net, min(start[0], goal[0]), max(start[0], goal[0]),
                min(start[1], goal[1]), max(start[1], goal[1])))

    def in_bounds(self, x, y):
        """Inside the scope's extent.

        Load bearing. `TrackMap.track_at` returns the NEAREST track, so
        it answers for coordinates far outside the cell too, and without
        this the grid is unbounded and the search wanders off into empty
        space forever. The first run did not terminate in five minutes
        for exactly this reason.
        """
        x1, y1, x2, y2 = self.tm.extent
        return x1 <= x <= x2 and y1 <= y <= y2

    def neighbours(self, node):
        """(node, cost) reachable in one move."""
        x, y, layer = node
        out = []
        horizontal = self.tm.directions.get(layer) == "h"

        #- a step along the layer's own direction. A horizontal layer
        #- steps in x at the horizontal pitch; a vertical one in y at
        #- the vertical pitch.
        step = self.tm.hpitch if horizontal else self.tm.vpitch
        for delta in () if layer in self.pin_only else (-step, step):
            nx, ny = (x + delta, y) if horizontal else (x, y + delta)
            if not self.in_bounds(nx, ny):
                continue
            lo, hi = sorted(((x, nx) if horizontal else (y, ny)))
            if self.is_free(layer, y if horizontal else x, lo, hi):
                out.append(((nx, ny, layer), abs(delta)))

        #- a via to an adjacent layer, if the column is clear. Asked
        #- once, not once per neighbouring layer: the column does not
        #- care which layer is being left.
        for other in self._adj[layer]:
            if self.via_is_free(x, y, layer, other):
                out.append(((x, y, other), self.via_cost))
        return out

    #-----------------------------------------------------------------
    #- from a path to geometry
    #-----------------------------------------------------------------

    def segments(self, path):
        """Collapse a path into (layer, x1, y1, x2, y2) runs and vias.

        Returns (runs, vias). A run is consecutive nodes on one layer; a
        via is a point where the layer changed. Emitted separately
        because they are checked separately -- a run against track
        occupancy, a via against the column.
        """
        runs, vias = [], []
        if not path:
            return runs, vias
        start = path[0]
        for prev, node in zip(path, path[1:]):
            if node[2] != prev[2]:
                #- A layer change ends the run and makes a via. A run of
                #- ZERO length is not emitted: it is a point, and the
                #- only thing there is the via, which already lands on
                #- whatever it is joining. Emitting it anyway put a
                #- small square of metal on the pin layer beside the
                #- device rails and produced 14 li.3 spacing errors.
                if (start[0], start[1]) != (prev[0], prev[1]):
                    runs.append((prev[2], start[0], start[1], prev[0], prev[1]))
                vias.append((prev[2], node[2], prev[0], prev[1]))
                start = node
        last = path[-1]
        if (start[0], start[1]) != (last[0], last[1]):
            runs.append((last[2], start[0], start[1], last[0], last[1]))
        return runs, vias

    @staticmethod
    def pin_centre(rect):
        return (int((rect.x1 + rect.x2) / 2), int((rect.y1 + rect.y2) / 2))

    def connect(self, layout, a_rect, b_rect, layer=None, width=None):
        """Search between two pin rects and draw the result.

        The convenience the pycells want: give it two pins, get geometry
        or a Blocked with a reason. Deliberately explicit about WHICH
        two pins -- picking them automatically needs the connectivity
        components, and guessing them is how a router quietly adds a
        redundant route that shorts something.
        """
        layer = layer or getattr(a_rect, "layer", None) or self.tm.pin_layer
        self._own = [a_rect, b_rect]
        start = (*self.pin_centre(a_rect), layer)
        goal = (*self.pin_centre(b_rect), layer)
        path = self.search(start, goal, self.manhattan_heuristic(self.snap(goal)))
        return self.emit(layout, path, width=width)

    def emit(self, layout, path, width=None):
        """Draw `path` into `layout`. Returns (rects, cuts) counts.

        This is the only part of the router that mutates anything, kept
        apart from the search on purpose: a path can be inspected,
        asserted on and diffed without a layout ever changing.
        """
        from cicpy.core.cut import Cut
        from cicpy.core.rect import Rect
        runs, vias = self.segments(path)
        nrect = 0
        for layer, x1, y1, x2, y2 in runs:
            #- the technology's width, not the track pitch. They happen
            #- to be equal here, which is exactly why the two were
            #- confused and why adjacent tracks abutted.
            w = width or self.rule(layer, "width")
            half = w // 2
            #- A run must be long enough to satisfy the layer's minimum
            #- area. The technology carries `minlength` for this --
            #- min area divided by the routing width -- because area is
            #- not a length and cannot be scaled by gamma like the rest.
            #- Without it a one step run is 3000 x 3000 = 0.09 um2
            #- against met3's 0.24 minimum, and every short segment the
            #- router draws is a met3.6 error.
            try:
                minlen = self.rule(layer, "minlength")
            except Exception:
                minlen = w
            lx, hx = sorted((x1, x2))
            ly, hy = sorted((y1, y2))
            if lx == hx:
                lx, hx = lx - half, hx + half
            if ly == hy:
                ly, hy = ly - half, hy + half
            #- grow the long axis to minlength, about its own centre so
            #- the run still covers what it was routed to cover
            if (hx - lx) >= (hy - ly):
                if (hx - lx) < minlen:
                    c = (lx + hx) // 2
                    lx, hx = c - minlen // 2, c + minlen - minlen // 2
            elif (hy - ly) < minlen:
                c = (ly + hy) // 2
                ly, hy = c - minlen // 2, c + minlen - minlen // 2
            #- built directly rather than through addRectangle so the
            #- NET can be set. Without it the rect comes back as "?" on
            #- the next map rebuild and the router cannot tell its own
            #- earlier geometry from a foreign net's.
            rr = Rect(layer, int(lx), int(ly), int(hx - lx), int(hy - ly))
            rr.setNet(self.net)
            layout.add(rr)
            nrect += 1
        #- Landing pads. A cut is 4000 square here and a routing wire
        #- 3000 wide, so the wire does not even COVER the via, let alone
        #- enclose it: every via drawn without a pad is an mcon.1 /
        #- via3.1 width error and takes its neighbours with it. The pad
        #- is the cut plus the layer's own enclosure rule on each side,
        #- on BOTH layers the via joins.
        for a_layer, b_layer, x, y in vias:
            cw, ch = self.via_extent(a_layer, b_layer)
            for lay in (a_layer, b_layer):
                enc = self.via_enclosure(lay, a_layer, b_layer)
                pw, ph = cw + 2 * enc, ch + 2 * enc
                rr = Rect(lay, int(x - pw // 2), int(y - ph // 2),
                          int(pw), int(ph))
                rr.setNet(self.net)
                layout.add(rr)
                nrect += 1

        ncut = 0
        for a_layer, b_layer, x, y in vias:
            #- getInstance already returns a FRESH InstanceCut each call
            #- and registers the cut cell in Cut._cuts, which is what
            #- Design.addCuts() later hoists into the design. Taking a
            #- getCopy() of it instead produced something the printer
            #- did not recognise as an instance: the wires appeared in
            #- the .mag and not one via did, so every routed net stayed
            #- open with nothing to show why.
            inst = Cut.getInstance(a_layer, b_layer, 1, 1)
            if inst is None:
                continue
            inst.moveCenter(int(x), int(y))
            inst.updateBoundingRect()
            layout.add(inst)
            ncut += 1
        return nrect, ncut

    #-----------------------------------------------------------------

    @staticmethod
    def _manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def manhattan_heuristic(self, goal):
        """Admissible: never over-estimates, since a via costs extra on
        top of the distance it does not shorten."""
        return lambda n: self._manhattan(n, goal)

    @staticmethod
    def _unwind(prev, node):
        path = [node]
        while node in prev:
            node = prev[node]
            path.append(node)
        return list(reversed(path))


#- --------------------------------------------------------------------
#- Hierarchical routing: stack, then group, then top
#- --------------------------------------------------------------------
#- The large-net problem dissolves if it is never posed. VO has three
#- pins in two stacks; routed whole it is a haul across the cell that
#- collides with everything between. Routed stack-first it is one
#- two-pin route inside xba and one hop between stacks.
#-
#- Measured on LELOTEMP_OTAR: 13 nets of up to 33 pins become 19
#- stack-level subproblems and 13 inter-stack hops, and 27 of 28
#- subproblems are routable when scoped to their own stack -- including
#- all five ladder nets, which whole-cell routing could only get 3 of.

def stack_of(instance_name):
    """The stack an instance belongs to.

    Same rule ciccreator uses for placement groups: the leading
    non-digit run of the name (subcktinstance.cpp:24). XA1/XA2 are one
    stack, XR1/XM1 are two.
    """
    import re as _re
    m = _re.match(r"^([^\d<>]+)", instance_name or "")
    return m.group(1) if m else ""


def stack_membership(layout):
    """{instance name: stack name}, from the design's own CellGroups.

    A stack is a StackGroup. Identified by TYPE, not by shape: a
    StackGroup's children include RouteBundles, which carry `.instances`
    too, so "a group with instances and no sub-groups" walks past the
    real stack onto a bundle -- and bundles have no tap_instances, so
    every tap then falls into a pseudo-stack of its own.

    Falls back to the leading non-digit run of the instance name, which
    is ciccreator's placement-group rule, when a design has no groups --
    a .cic reloaded from disk has none.
    """
    from cicpy.core.cellgroup import CellGroup, StackGroup
    member = {}

    def _walk(grp):
        if isinstance(grp, StackGroup):
            gname = getattr(grp, "name", "")
            for inst in (list(getattr(grp, "instances", []))
                         + list(getattr(grp, "tap_instances", []))):
                nm = getattr(inst, "instanceName", "") or ""
                if nm and gname:
                    member[nm] = gname
            return  #- below a stack is routing, not placement
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                _walk(c)

    for grp in getattr(layout, "cellgroups", []) or []:
        _walk(grp)
    return member


def stack_groups(layout):
    """{stack name: the StackGroup itself}.

    The group, not just its instance names, because
    CellGroup.addConnectivityRoute scopes itself -- it builds its own
    instanceRegex and takes a different path through getNodeAccessRects
    than passing includeInstances by hand does. The hand written routes
    that worked in this design all went through the group.
    """
    from cicpy.core.cellgroup import CellGroup, StackGroup
    out = {}

    def _walk(grp):
        if isinstance(grp, StackGroup):
            nm = getattr(grp, "name", "")
            if nm:
                out[nm] = grp
            return
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                _walk(c)

    for grp in getattr(layout, "cellgroups", []) or []:
        _walk(grp)
    return out


def pins_by_stack(layout, layer=None):
    """{stack: {net: [rect, ...]}} for everything the node graph knows."""
    from collections import defaultdict
    if layer is None:
        from cicpy.core.trackmap import TrackMap
        layer = TrackMap(layout).pin_layer
    out = defaultdict(lambda: defaultdict(list))
    member = stack_membership(layout)
    for net in getattr(layout, "nodeGraphList", []):
        g = layout.nodeGraph.get(net)
        if g is None:
            continue
        for port in getattr(g, "ports", []):
            inst = getattr(port, "parent", None)
            name = getattr(inst, "instanceName", "") if inst else ""
            rect = port.get(layer) if hasattr(port, "get") else None
            if name and rect is not None:
                out[member.get(name) or stack_of(name)][net].append(rect)
    return out


def route_spec(path, tm, claimed=(), router=None, pins=None):
    """Turn a searched path into a route.py command, or None.

    The search decides WHERE a net should go; route.py knows how to
    DRAW it -- widths, via enclosures, cut placement, alignment, all of
    which it has been getting right for years. Emitting raw rects and
    cut instances instead reimplements that badly: it is what produced
    272 DRC errors of minimum width, minimum area and via enclosure, and
    what makes a route look hand stitched rather than routed.

    So the router's output here is a (layer, routeType, options) triple
    for `addConnectivityRoute`, not geometry.

    Returns None when the path is not a shape route.py can express --
    a staircase across several layers has no route type -- and the
    caller should then leave the net alone rather than draw something
    route.py would not have.
    """
    if not path or len(path) < 2:
        return None
    xs = {n[0] for n in path}
    ys = {n[1] for n in path}
    ends = (path[0][2], path[-1][2])

    #- A path ALWAYS changes layer, so "is it one layer" is never the
    #- question. The pin layer is pin-only -- a route may via off it and
    #- not run along it -- so the search has to leave it to move at all,
    #- and every pin-to-pin path reads as M1 -> M2 -> ... -> M1.
    #-
    #- What matters is the SHAPE. A path with one x is a vertical, one y
    #- a horizontal, whatever it did about layers on the way.
    opts = ""
    trunk = None
    if len(xs) == 1 and len(ys) > 1:
        rtype = "||"
    elif len(ys) == 1 and len(xs) > 1:
        rtype = "-"
    elif len(xs) > 1 and len(ys) > 1:
        #- A bend. route.py draws these as a vertical TRUNK with
        #- horizontal branches off it -- "-|--" puts the trunk left of
        #- the pins, "--|-" right -- which is the same shape a search
        #- returns whenever the two pins share neither row nor column.
        #- Refusing them left every ladder net in p_sw unrouted, and
        #- they are the majority of what a stack needs: pins at
        #- different heights in different columns.
        #-
        #- Which side the trunk goes on is not cosmetic. It is where the
        #- search FOUND room, so take it from the path: the trunk is the
        #- column the path spends its vertical run in.
        by_x = {}
        for x, y, _l in path:
            by_x.setdefault(x, set()).add(y)
        #- ...and not a column another net in this stack already took.
        #- The map is rebuilt per net, but route.py does not DRAW until
        #- after beforeRoute returns, so every search in a stack sees a
        #- column nobody has claimed yet and four of five ladder nets
        #- picked the same one. What the searches cannot see from each
        #- other, the caller remembers for them.
        free = [x for x in by_x if x not in claimed] or list(by_x)
        trunk = max(free, key=lambda x: (len(by_x[x]), -x))
        rtype = "-|--" if trunk <= (min(xs) + max(xs)) // 2 else "--|-"
        #- and SAY where. Without this route.py places the trunk from
        #- the net's own pins, so five ladder nets in one column each
        #- compute the same lane and land on it: measured, one component
        #- holding VCP and net1..net5. The search already picked a column
        #- with room in it -- per net, against a map that has the last
        #- route in it -- and trunkx is route.py's way of being told.
        opts = f"trunkx={trunk}"
    else:
        return None

    #- INSIDE A STACK, THE PIN LAYER.
    #-
    #- A link between two devices in one column is a short local hop and
    #- its pins are already on the pin layer: no via, no landing pad, and
    #- no track spent on a layer the group level wants for crossing the
    #- cell. r_deg's R1<0> is exactly that -- two terminals one row apart
    #- in the same column -- and it routes clean on M1.
    #-
    #- This was briefly forced onto a routing layer because the p_sw
    #- ladder shorted on M1, and that was the wrong conclusion drawn from
    #- a real failure: it moved a finished stack off the layer it should
    #- be on to fix a different stack, which it did not fix either. The
    #- ladder's problem is five nets wanting five trunks in an 8 micron
    #- column, and no layer choice makes that fit.
    #-
    #- "If possible" cannot be asked of is_free, and that is worth
    #- recording: the pin layer is pin-only, so it has no entry in
    #- ROUTE.directions and the track map holds no tracks for it. is_free
    #- then answers False for every corridor on it -- not because
    #- anything is in the way, but because it has nothing to look at.
    layer = ends[0] if ends[0] == ends[1] else None
    if layer is None:
        vertical = rtype in ("||", "-|--", "--|-")
        want = "v" if vertical else "h"
        on_path = [n[2] for n in path if n[2] != tm.pin_layer]
        candidates = ([l for l in on_path if tm.directions.get(l) == want]
                      or [l for l, d in tm.directions.items() if d == want]
                      or on_path)
        if not candidates:
            return None
        layer = candidates[0]

    return (layer, rtype, opts, trunk)


def supply_nets(layout):
    """Nets that a device ties its BULK to -- power and ground.

    From the netlist, not from a name list: "VDD" and "VSS" are this
    design's spelling and a router that greps for them is a router for
    this design. Every device declares its body terminal, and a net on
    a body terminal is a supply by construction.
    """
    out = set()
    for net in getattr(layout, "nodeGraphList", []):
        g = layout.nodeGraph.get(net)
        if g is None:
            continue
        for port in getattr(g, "ports", []):
            if (getattr(port, "childName", "") or "").upper() == "B":
                out.add(net)
                break
    return out


def _internal_nets(layout, stack):
    """Nets wholly inside `stack` -- one source, shared with the plan.

    Not recomputed here on purpose: the stack cell's port list and the
    set of nets the stack level routes have to be the same set, or the
    layout closes a net the generated subckt still calls a port.
    """
    for entry in plan_stack_cells(layout):
        if entry["stack"] == stack:
            return set(entry["internal"])
    return set()


def route_stack_level(layout, margin=8000, log=None, only=None):
    """Route every net inside every stack. Returns (routed, blocked).

    Level one of three. Each stack is solved against its OWN extent, so
    a route here cannot see -- or collide with -- anything in another
    stack, and the search has the room that whole-cell routing has
    already spent. Nets with one pin in a stack are left alone: there is
    nothing to join, and the hop to the next stack is the next level's
    problem.

    The map is rebuilt per net because a route just drawn is an obstacle
    for the next.
    """
    from cicpy.core.trackmap import TrackMap
    log = log or logging.getLogger("MazeRouter")
    routed, blocked = [], []
    by_stack = pins_by_stack(layout)
    groups = stack_groups(layout)
    #- `only` names the stacks to route. One at a time is the sane way
    #- to bring this up: a stack that is not clean is then the only
    #- thing that can have made the layout dirty, and the next one
    #- starts from a known good state instead of from a pile.
    wanted = None
    if only:
        wanted = {only} if isinstance(only, str) else set(only)
    for stack in sorted(by_stack):
        if wanted is not None and stack not in wanted:
            continue
        #- INTERNAL nets only. A net that also has pins outside this
        #- stack is a boundary net and belongs to the next level up:
        #- routing it here joins the pins that happen to be inside and
        #- calls the net done, while the rest of it is still elsewhere.
        #-
        #- Measured, on p_sw: VCP has two pins in the ladder column and
        #- more outside it, and a stack level vertical between them runs
        #- the length of a SERIES chain -- so it crosses the pin of every
        #- intermediate node and shorts VCP to net1..net5 in one command.
        #- The same shape at group level has the whole column to get
        #- around them with. This is the hierarchy doing its job, not a
        #- restriction on it.
        internal = _internal_nets(layout, stack)
        subs = {n: rs for n, rs in by_stack[stack].items()
                if len(rs) >= 2 and n in internal}
        if not subs:
            continue
        insts_in_stack = sorted({n for n, st in stack_membership(layout).items()
                                 if st == stack})
        allr = [r for v in by_stack[stack].values() for r in v]
        extent = (min(r.x1 for r in allr) - margin,
                  min(r.y1 for r in allr) - margin,
                  max(r.x2 for r in allr) + margin,
                  max(r.y2 for r in allr) + margin)
        claimed = set()
        #- POWER AND GROUND FIRST. They are the widest, the least free
        #- to detour and the ones every other route has to clear, so a
        #- signal placed before them takes a track a supply then cannot
        #- give up. Ordering is the cheapest form of rip-up there is:
        #- the constrained net picks first.
        supplies = supply_nets(layout)
        order = sorted(subs, key=lambda n: (n not in supplies, n))
        for net in order:
            rects = subs[net]
            tm = TrackMap(layout, block_pins=True, extent=extent).build()
            r = MazeRouter(tm, net)
            try:
                #- Search for the shape, then hand it to route.py. The
                #- search proves a path exists and says which layer and
                #- direction it wants; the drawing is not ours to do.
                specs = []
                for a, b in zip(rects, rects[1:]):
                    layer = getattr(a, "layer", None) or tm.pin_layer
                    start = (*r.pin_centre(a), layer)
                    goal = (*r.pin_centre(b), layer)
                    r._own = [a, b]
                    path = r.search(start, goal,
                                    r.manhattan_heuristic(r.snap(goal)))
                    spec = route_spec(path, tm, claimed, r, (a, b))
                    if spec is None:
                        raise Blocked(
                            f"path for {net} is not a shape route.py can "
                            f"draw ({len(path)} nodes, layers "
                            f"{sorted({n[2] for n in path})})")
                    specs.append(spec)
                #- one command per net: route.py finds the net's own
                #- rects, so a repeated spec would redraw the same thing
                #- Scoped to this stack's instances. route.py finds a
                #- net's own rects, and without the scope it would take
                #- every pin of the net in the whole cell -- which is
                #- the top level route this is replacing.
                layer, rtype, opts, trunk = specs[0]
                if trunk is not None:
                    claimed.add(trunk)
                grp = groups.get(stack)
                if grp is None:
                    raise Blocked(f"no group object for stack {stack}")
                grp.addConnectivityRoute(layer, f"^{re.escape(net)}$",
                                         rtype, opts, 1)
                routed.append((stack, net))
            except Blocked as e:
                blocked.append((stack, net, str(e)))
                log.warning(f"{stack}/{net}: {e}")
    return routed, blocked


def plan_stack_cells(layout, parent_name=None):
    """What subcells the stacks would become, without making any.

    Returns [{name, stack, instances, ports, internal}] where `ports`
    are the nets that cross the stack boundary -- the ones the parent
    still has to route -- and `internal` are the nets wholly inside it,
    which the stack owns and nobody above needs to see.

    Deliberately analysis only. Turning a group into a real subcell
    means three separate things, and knowing the shape first is what
    makes them separable:

      1. a LayoutCell registered in design.cells, or no .mag is written
         for it. Nesting alone does NOT do this: DesignPrinter flattens
         a nested LayoutCell into its parent
         (designprinter.py: `elif child.isLayoutCell(): printChildren`).
      2. an Instance of it in the parent, so the parent references
         rather than contains.
      3. a subckt for the schematic side, synthesised from the devices
         in the stack with the boundary nets as its ports -- LVS needs
         something to compare the extracted stack against, and the
         xschem source has no such hierarchy.

    The port list is the whole payoff. Everything in `internal` stops
    existing as far as the parent is concerned.
    """
    from collections import defaultdict
    counts = defaultdict(lambda: defaultdict(int))
    insts = defaultdict(list)
    #- The CellGroups the design actually built, when it built any.
    #- The name-prefix rule is a fallback and it is WRONG for taps and
    #- fillers: addTaps names them after the GROUP (xstack_n_load_a_bot)
    #- while the devices are named by prefix (xnd, xns), so a prefix
    #- grouping puts every tap in a one-instance stack of its own --
    #- measured, 17 bogus stacks out of 25.
    #- One definition of "which stack is this instance in", shared with
    #- pins_by_stack. They used to disagree -- this walked the
    #- CellGroups and gave r_deg, that used the name prefix and gave xd
    #- -- so asking the router to route "r_deg" matched nothing and
    #- reported 0 routed, 0 blocked, which reads exactly like success.
    member = stack_membership(layout)

    for inst in layout.iterInstances():
        name = getattr(inst, "instanceName", "") or ""
        st = member.get(name) or stack_of(name)
        if not st:
            continue
        insts[st].append(name)
        member[name] = st
    for net in getattr(layout, "nodeGraphList", []):
        g = layout.nodeGraph.get(net)
        if g is None:
            continue
        for port in getattr(g, "ports", []):
            inst = getattr(port, "parent", None)
            nm = getattr(inst, "instanceName", "") if inst else ""
            if nm:
                counts[member.get(nm) or stack_of(nm)][net] += 1
    #- how many stacks does each net appear in?
    spread = defaultdict(int)
    for st in counts:
        for net in counts[st]:
            spread[net] += 1
    out = []
    for st in sorted(insts):
        nets = counts.get(st, {})
        ports = sorted(n for n in nets if spread[n] > 1)
        internal = sorted(n for n in nets if spread[n] == 1)
        out.append({
            "name": f"{parent_name or layout.name}_{st}".upper(),
            "stack": st,
            "instances": sorted(insts[st]),
            "ports": ports,
            "internal": internal,
        })
    return out


def stack_subckt(layout, entry):
    """Synthesise the schematic side of a stack subcell.

    Returns (lines, fingerprint). The lines are a spice subckt built
    from the devices actually in the stack, with the boundary nets as
    its ports; the fingerprint is what those devices and their
    connections are, so a silent change can be detected.

    GENERATED, never edited. That is the answer to the obvious worry
    about a hand-maintained substack schematic drifting from the layout:
    there is nothing to drift, because both sides come from the same
    netlist and grouping and are rebuilt together every run.

    The fingerprint guards the one thing regeneration cannot: the
    GROUPING changing without anyone noticing. Instance names decide
    placement groups (ciccreator subcktinstance.cpp:24), so a rename
    silently moves a device to another stack -- and both the schematic
    and the layout would then agree, wrongly and consistently.
    """
    import hashlib
    devices = []
    for inst in layout.iterInstances():
        name = getattr(inst, "instanceName", "") or ""
        if name not in entry["instances"]:
            continue
        nodes = list(getattr(inst, "instancePortsList", []) or [])
        #- the SCHEMATIC cell, not the layout one. They differ for a
        #- diode connected device, which is placed as the D variant.
        cell = (getattr(inst, "schematicCell", "")
                or getattr(inst, "cell", "") or "")
        #- Skip instances with no nodes. Taps and fillers are LAYOUT,
        #- not circuit: the parent netlist has no such devices either,
        #- they are added by the placement. Emitting them produced a
        #- schematic the printer refused --
        #-   instance xfill_p_sw_0: []
        #-   cell REYATR_PCH_4C1F2D: ['D','G','S','B']
        #- and they would have had nothing to match in LVS anyway, since
        #- they extract as geometry rather than as devices.
        if not nodes:
            continue
        devices.append((name, nodes, cell))
    devices.sort()
    ports = list(entry["ports"])
    lines = [f".subckt {entry['name']} {' '.join(ports)}"]
    for name, nodes, cell in devices:
        lines.append(f"{name} {' '.join(nodes)} {cell}")
    lines.append(".ends")
    key = "|".join(f"{n}:{c}:{','.join(nd)}" for n, nd, c in devices)
    key += "||" + ",".join(sorted(ports))
    return lines, hashlib.sha1(key.encode()).hexdigest()[:12]


def design_of(layout):
    """The Design a layout belongs to.

    `layout.design` is None during a pycell hook -- it is set later --
    so a hook that asks for it silently does nothing. `layout.parent` is
    the MagicDesign and is set, which is the same route cellgroup.py
    already takes to reach getLayoutCell.
    """
    for attr in ("design", "parent"):
        d = getattr(layout, attr, None)
        if d is not None and hasattr(d, "cells") and hasattr(d, "cellnames"):
            return d
    return None


def _run_stack_pycell(layout, cell, entry, log):
    """Run <STACKCELL>.py if the design ships one.

    Divide and conquer, using the mechanism that already exists: a cell
    can have a pycell beside it, so a stack cell can too. Same lookup as
    cic.py's -- dirname + name + ".py" on sys.path -- so a stack's
    routing lives in its own file rather than as another paragraph in
    the parent's.

    The hook is `route(cell, layout, entry)`: the stack cell being
    built, the parent it came from, and its plan entry. The parent is
    passed because the node graph belongs to it -- a stack cell holds
    the instances but not the netlist, so its pins are only findable
    through the parent until the flow builds each stack from its own
    generated subckt.
    """
    import importlib
    import os
    import sys
    dirname = getattr(layout, "dirname", "") or ""
    path = os.path.join(dirname, cell.name + ".py")
    if not os.path.exists(path):
        return False
    if dirname not in sys.path:
        sys.path.append(dirname)
    try:
        mod = importlib.import_module(cell.name)
        importlib.reload(mod)
    except Exception as e:
        log.error(f"{cell.name}: pycell failed to import: {e}")
        return False
    fn = getattr(mod, "route", None)
    if fn is None:
        return False
    try:
        fn(cell, layout, entry)
        log.info(f"{cell.name}: routed by its own pycell")
        return True
    except Exception as e:
        log.error(f"{cell.name}: pycell route() raised: {e}")
        return False


def write_stack_cells(layout, design=None, plan=None, log=None):
    """Register each stack as a real cell so a .mag is written for it.

    Returns [(name, fingerprint, ports)].

    This is the standalone-verification step, and deliberately NOT the
    restructuring one. The parent keeps its instances; each stack is
    additionally published as a cell holding the same instances, with
    its boundary nets as ports. That is enough to get a .mag and a
    netlist per stack and to LVS each one ALONE -- which is the gate the
    hierarchy needs -- without disturbing a parent that currently works.

    Turning the parent into a cell that REFERENCES these rather than
    containing them is a separate change, and it should not be made
    until the standalone LVS passes: it is the difference between
    "generate and check" and "generate, check, and rely on".
    """
    from cicpy.core.layoutcell import LayoutCell
    log = log or logging.getLogger("MazeRouter")
    design = design if design is not None else design_of(layout)
    if design is None:
        log.warning("no design reachable from the layout; no stack cells written")
        return []
    plan = plan if plan is not None else plan_stack_cells(layout)
    made = []
    for entry in plan:
        name = entry["name"]
        if name in getattr(design, "cells", {}):
            continue
        cell = LayoutCell()
        cell.name = name
        cell.design = design
        #- Bound from the INSTANCES, not from every rect, so a route
        #- drawn inside a stack cannot inflate the placement box.
        #-
        #- It does NOT explain the size, and that was measured before
        #- assuming it did. A stack is as wide as the device columns it
        #- holds plus 0.480 of guard: P_SW 8.480 for one 8.000 column,
        #- R_DEG 16.480 for two. That 0.480 is the ring each REYATR cell
        #- overhangs its box with so that abutted columns MERGE their
        #- guards -- shared in the parent, and paid in full by a stack
        #- standing alone. The size is right; there is nothing to trim.
        #-
        #- What does look wrong is the position: these cells keep the
        #- parent's absolute coordinates (R_DEG at x 24.000, P_SW at
        #- y 32.300), so reading extents straight out of the .mag makes
        #- them appear to start far from the origin.
        cell.boundaryIgnoreRouting = True
        wanted = set(entry["instances"])
        for inst in layout.iterInstances():
            if (getattr(inst, "instanceName", "") or "") in wanted:
                cell.add(inst)
        #- The routing that belongs to this stack. Without it the cell
        #- holds devices and no wires, so its layout extracts as one net
        #- per terminal: measured on P_IN_A, 7 devices and 22 nets
        #- against the schematic's 5 -- with the DEVICE count matching
        #- exactly, which is how it was clear the decomposition was
        #- right and only the wires were missing.
        #-
        #- A stack's routing is the geometry inside its own bounds,
        #- which is what a stack-level router would produce and what the
        #- parent currently produces. Copies, not moves: the parent
        #- still needs its geometry, and this cell is published
        #- alongside it rather than replacing it.
        cell.updateBoundingRect()
        sx1, sy1, sx2, sy2 = cell.x1, cell.y1, cell.x2, cell.y2
        #- The parent's ROUTING, and only that. Not
        #- _collectPhysicalRects: that flattens instance content too, so
        #- copying it duplicates every device's own geometry, which the
        #- instances already bring. Routed wires are not direct children
        #- either -- they live inside Route objects -- so this walks the
        #- non-instance children and takes the rects it finds.
        def _routed(node, out, depth=0):
            if depth > 6:
                return
            for ch in getattr(node, "children", []) or []:
                if ch is None:
                    continue
                if hasattr(ch, "isInstance") and ch.isInstance():
                    continue
                if hasattr(ch, "isPort") and ch.isPort():
                    continue
                if hasattr(ch, "isRect") and ch.isRect():
                    out.append(ch)
                else:
                    _routed(ch, out, depth + 1)

        routed = []
        _routed(layout, routed)
        added = 0
        for r in routed:
            if (r.x1 >= sx1 and r.x2 <= sx2
                    and r.y1 >= sy1 and r.y2 <= sy2):
                cell.add(r.getCopy())
                added += 1
        log.info(f"{name}: {added} routed rects of {len(routed)} inside")

        #- the boundary nets, as ports, from the pins that carry them
        pins = {}
        for net in entry["ports"]:
            g = layout.nodeGraph.get(net)
            if g is None:
                continue
            for port in getattr(g, "ports", []):
                pinst = getattr(port, "parent", None)
                nm = getattr(pinst, "instanceName", "") if pinst else ""
                if nm not in wanted:
                    continue
                rect = port.get() if hasattr(port, "get") else None
                if rect is not None:
                    pins.setdefault(net, rect)
                    break
        for net, rect in pins.items():
            try:
                cell.addPort(net, rect)
            except Exception as e:
                log.warning(f"{name}: could not add port {net}: {e}")
        cell.updateBoundingRect()
        lines, fp = stack_subckt(layout, entry)
        cell.cic_subckt = lines
        cell.cic_fingerprint = fp
        #- Give the cell a real Subckt, parsed from the generated text.
        #- Subckt.parse takes spice lines, so the generated netlist and
        #- the object the printers want are the same thing rather than
        #- two representations to keep in step.
        try:
            from cicspi import Subckt
            #- the PARENT's parser. A Subckt built without one has no
            #- instance registry to resolve subcircuit references
            #- against, and parse() dies on the first device with
            #- "NoneType has no attribute allinst".
            parser = getattr(getattr(layout, "ckt", None), "parser", None)
            if parser is None:
                parser = getattr(Subckt, "circuits", None)
            ckt = Subckt(parser)
            ckt.parse(list(lines), 0)
            cell.ckt = ckt
        except Exception as e:
            log.warning(f"{name}: could not build a subckt: {e}")
        design.cells[name] = cell
        if hasattr(design, "cellnames") and name not in design.cellnames:
            #- ahead of the parent, so it is defined before it is used
            design.cellnames.insert(0, name)
        _run_stack_pycell(layout, cell, entry, log)
        made.append((name, fp, sorted(pins)))
        log.info(f"stack cell {name}: {len(wanted)} instances, "
                 f"{len(pins)} ports, fp={fp}")
    return made


#- Schematics for the stack cells are NOT written from here, and an
#- attempt to do it was reverted. Driving XschemPrinter by hand from a
#- pycell hook does not work: symbolAndWrite RETURNS SILENTLY when a
#- referenced cell is missing from printer.cells
#- (xschemprinter.py:368), and at that point in the flow design.cells
#- holds exactly one cell -- the top. The result is a schematic with
#- every symbol and not one wire, which xschem then netlists as empty,
#- and LVS reports the CDL as having "no elements and/or nodes". No
#- warning is produced anywhere along that path.
#-
#- The stack cells are registered in the design, so they are in the
#- .cic, and the ordinary transpile writes them correctly because it
#- populates printer.cells as it iterates:
#-
#-   cicpy transpile <cell>.cic <tech> <LIB> --xschem --I <deps>
#-
#- 24 wires on LELOTEMP_OTAR_P_SW that way, against 0 by hand.


