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
routing failure measured so far has turned out to be.

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

    #- Bucket size for the pin index, in routing pitches. Coarse on
    #- purpose: it only has to cut the candidate set down, and an exact
    #- overlap test runs after. Counted in pitches rather than database
    #- units so it stays the same SIZE OF NEIGHBOURHOOD in a technology
    #- with different units -- as a literal 20000 it was either every
    #- pin in one bucket or one pin per bucket, and both are the linear
    #- scan the index exists to avoid.
    BUCKET_PITCHES = 5

    @property
    def BUCKET(self):
        return self.BUCKET_PITCHES * max(self.tm.hpitch, self.tm.vpitch)

    def _index_foreign_pins(self):
        """Every pin not belonging to this net, bucketed by position.

        `column_blockers` walks every track on every layer, which is
        fine for a question asked once and ruinous for one asked per
        node expansion: on a cell of a couple of thousand rects the
        first search did not finish in five minutes. The obstacles do not change during a
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

        That is what shorts two nets a track apart: each is legal on its own
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

    def via_is_free(self, x, y, a_layer=None, b_layer=None, cut_wh=None):
        """Can this net drop a via column at (x, y)?

        The column is the cut's real size and claims every layer, so this is
        where two nets most often collide -- and it is exactly what
        `column_blockers` was built to answer. ``cut_wh`` asks about a
        specific cut array's extent instead of the single-cut default,
        which is how the emitter sizes up to 2x1/1x2.
        """
        routing = [l for l in self._layers if l not in self.pin_only]
        d0 = routing[0] if routing else (self._layers[0] if self._layers else "")
        d1 = routing[1] if len(routing) > 1 else d0
        w, h = cut_wh or self.via_extent(a_layer or d0, b_layer or d1)
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
        #-
        #- The pin layer is travelled only when the technology said so
        #- (ROUTE.pintravel), and then it is usually the CHEAPEST
        #- (ROUTE.costs): a wire that stays on the metal its pins live
        #- on needs no via, no landing pad, and no track on a layer the
        #- level above wants. What made this safe to allow is instance
        #- attribution -- the device rails that used to be invisible
        #- are hard obstacles now, so a cheap M1 path cannot be a
        #- quietly wrong one.
        travel_ok = (layer not in self.pin_only
                     or getattr(self.tm, "pin_travel", ""))
        step = self.tm.hpitch if horizontal else self.tm.vpitch
        weight = self.tm.layer_cost(layer)
        for delta in (-step, step) if travel_ok else ():
            nx, ny = (x + delta, y) if horizontal else (x, y + delta)
            if not self.in_bounds(nx, ny):
                continue
            lo, hi = sorted(((x, nx) if horizontal else (y, ny)))
            if self.is_free(layer, y if horizontal else x, lo, hi):
                out.append(((nx, ny, layer), abs(delta) * weight))

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
        ncut = 0
        for a_layer, b_layer, x, y in vias:
            #- getInstance already returns a FRESH InstanceCut each call
            #- and registers the cut cell in Cut._cuts, which is what
            #- Design.addCuts() later hoists into the design. Taking a
            #- getCopy() of it instead produced something the printer
            #- did not recognise as an instance: the wires appeared in
            #- the .mag and not one via did, so every routed net stayed
            #- open with nothing to show why.
            #-
            #- A lone via is the last resort, not the default: try the
            #- two-cut arrays first, in both orientations, and take the
            #- first whose extent the neighbourhood accepts. The space
            #- question is via_is_free's, asked at the candidate's own
            #- size.
            inst = None
            for (hc, vc) in ((2, 1), (1, 2), (1, 1)):
                cand = Cut.getInstance(a_layer, b_layer, hc, vc)
                if cand is None:
                    continue
                if (hc, vc) != (1, 1) and not self.via_is_free(
                        x, y, a_layer, b_layer,
                        cut_wh=(int(cand.width()), int(cand.height()))):
                    continue
                inst = cand
                break
            if inst is None:
                continue
            inst.moveCenter(int(x), int(y))
            inst.updateBoundingRect()
            layout.add(inst)
            ncut += 1
            #- pads sized to the cut that was actually placed, on BOTH
            #- layers it joins: a cut is wider than the wire, so a via
            #- without its pad is an mcon.1 / via3.1 width error that
            #- takes its neighbours with it.
            cw, ch = int(inst.width()), int(inst.height())
            for lay in (a_layer, b_layer):
                enc = self.via_enclosure(lay, a_layer, b_layer)
                pw, ph = cw + 2 * enc, ch + 2 * enc
                rr = Rect(lay, int(x - pw // 2), int(y - ph // 2),
                          int(pw), int(ph))
                rr.setNet(self.net)
                layout.add(rr)
                nrect += 1
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
#- The large-net problem dissolves if it is never posed. A net with
#- three pins spread over two stacks, routed whole, is a haul across
#- the cell that collides with everything between. Routed stack-first
#- it is one two-pin route inside a stack and one hop between stacks.
#-
#- Measured on a mid-sized OTA: 13 nets of up to 33 pins become 19
#- stack-level subproblems and 13 inter-stack hops, and 27 of 28
#- subproblems are routable when scoped to their own stack -- including
#- a five-net series column that whole-cell routing could only get 3 of.

def stack_of(instance_name):
    """The stack an instance belongs to.

    Same rule ciccreator uses for placement groups: the leading
    non-digit run of the name (subcktinstance.cpp:24). XA1/XA2 are one
    stack, XR1/XM1 are two.
    """
    import re as _re
    m = _re.match(r"^([^\d<>]+)", instance_name or "")
    return m.group(1) if m else ""


def pins_by_stack(layout, layer=None):
    """{stack: {net: [rect, ...]}} for everything the node graph knows."""
    from collections import defaultdict
    if layer is None:
        from cicpy.core.trackmap import TrackMap
        layer = TrackMap(layout).pin_layer
    out = defaultdict(lambda: defaultdict(list))
    from .subcell import stack_membership
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
                #- which TERMINAL this pin is, carried on the rect. The
                #- router assigns lanes by it: a source net belongs on
                #- the left edge of its pins, a drain net on the right.
                rect.terminal = getattr(port, "childName", "") or ""
                rect.instName = name
                out[member.get(name) or stack_of(name)][net].append(rect)
    return out


def _terminal_lane(rects, layer, rtype):
    """A trunkx for a net that lives on one kind of terminal, or None.

    Left aligned on the sources, right aligned on the drains. The house
    style, and not for looks: S and D overlap in x on a compact cell,
    so two searched trunks land wherever there was room the moment each
    was asked -- often the same lane, always somewhere new. Assigned by
    terminal, every source net in the design shares the left lane,
    every drain net the right, they can never contest a track, and the
    drain lane stays clear of the gate tab that sits above the drain
    bar on this kind of library.

    Only for a vertical on pins that are ALL one terminal. A series
    link joins a D to an S and keeps the overlap the search found; a
    gate net lands on tabs that have no lane convention.
    """
    if rtype != "||" or not rects:
        return None
    terms = {getattr(r, "terminal", "") for r in rects}
    if len(terms) != 1:
        return None
    term = terms.pop()
    if term not in ("S", "D", "G"):
        return None
    try:
        w = int(Rules.getInstance().get(layer, "width"))
    except Exception:
        return None
    if term == "S":
        #- the left edge every pin shares
        edge = max(int(r.x1) for r in rects)
        return edge + w // 2
    if term == "D":
        edge = min(int(r.x2) for r in rects)
        return edge - w // 2
    #- a gate net lives on tabs: no S/D edge convention, and a tab is
    #- barely wider than the wire, so the lane is the tabs' common
    #- centre -- which also keeps the M1 test asking about the one
    #- column a gate wire can actually take
    ox1 = max(int(r.x1) for r in rects)
    ox2 = min(int(r.x2) for r in rects)
    if ox2 - ox1 < w:
        return None
    return (ox1 + ox2) // 2


def _pin_layer_if_clear(path, tm, router, pins, trunk, extent_rects=None):
    """The pin layer, but only where nothing else is on it. Else None.

    A link between two devices in one column is a short local hop and
    its pins are already on the pin layer: no via, no landing pad, and
    no track spent on a layer the group level wants for crossing the
    cell. That is the prize, and it is worth asking for.

    Whether it is ever earned depends on the cell library. One whose
    primitives keep their own metal off the pin layer will collect on
    it; one that runs internal straps there will not, and every stack
    falls through to a routing layer instead. Both are correct outcomes
    -- the test is cheap and the fallback costs two vias.

    "Clear" took three goes to ask correctly.

    It cannot be asked of `is_free`: the pin layer is pin-only, has no
    ROUTE.directions entry of its own, and so the map holds no tracks
    for it -- `is_free` answers False for every corridor, not because
    anything is there but because it has nothing to look at. That moved
    a stack off the pin layer that had every right to it.

    `column_blockers` is the right question for PINS, and it finds the
    real ones -- a power strap laid across a column's whole pin band is
    exactly what it is for. But a pin is all it can see. A device's own
    internal metal
    carries no net, arrives as "?", and is tolerated on the pin layer --
    it has to be, or a via could not land on a pin at all.

    That tolerance is a hole and the ladder fell through it.
    A transistor cell may run an unattributed strip up its side past
    both S and D, and in a compact library those two pins sit a few
    hundred nanometres apart and overlap in x. Routed on the pin layer,
    a series link then ties its device's D to its own S -- measured,
    magic extracted a six device chain as one node. So the corridor
    must be clear of unattributed metal too, and over the PINS' full
    span rather than the trunk's -- route.py lands on the whole pin, and
    the strip sits at the far left of a 22400 pin while the trunk is in
    the middle of it.

    Falling through to a routing layer costs two vias and is correct.
    """
    if not (tm.pin_layer and router is not None and path):
        return None
    if not (path[0][2] == path[-1][2] == tm.pin_layer):
        return None
    #- over the FULL span the drawn route will cover, not the span the
    #- search proved. route.py takes its trunk from every rect the net
    #- has in scope, so on a net of six pins the search's two-pin path
    #- is a fraction of the geometry: measured, a trunk drawn y
    #- 59000..223000 was cleared against a path reaching 99000 and ran
    #- straight through a gate pin at 173000.
    ys = [n[1] for n in path]
    xs = [n[0] for n in path]
    for r in (extent_rects or ()):
        ys.extend((int(r.y1), int(r.y2)))
        xs.extend((int(r.x1), int(r.x2)))
    col = trunk if trunk is not None else path[0][0]
    try:
        pad = Rules.getInstance().get(tm.pin_layer, "space")
    except Exception:
        pad = 0

    def _ok(c):
        try:
            if tm.column_blockers(router.net, c - pad, c + pad,
                                  min(ys), max(ys)) != []:
                return False
            if pins and len(pins) == 2:
                sx1 = min(p.x1 for p in pins) - pad
                sx2 = max(p.x2 for p in pins) + pad
            else:
                sx1, sx2 = c - pad, c + pad
            return tm.column_metal(router.net, tm.pin_layer, sx1, sx2,
                                   min(ys), max(ys)) == []
        except Exception:
            return False

    if _ok(col):
        return col
    #- The natural column is taken; the pin is wider than the wire.
    #- Scan the pins' COMMON window for a clear lane before giving up
    #- to a routing layer -- a compact library runs foreign bars
    #- through the middle of a wide pin, and the clear lane is off to
    #- the side. Measured: p_in's 28800 drain bar carries the source
    #- bar's shadow at its center, and the whole cell degraded to an
    #- M2 rail whose via pads then blocked the gate-tab lane.
    #- Right to left, since drains route right-aligned by convention.
    ext = list(extent_rects or ())
    if ext:
        try:
            w2 = Rules.getInstance().get(tm.pin_layer, "width") // 2
        except Exception:
            return None
        ox1 = max(int(r.x1) for r in ext) + w2
        ox2 = min(int(r.x2) for r in ext) - w2
        if ox2 <= ox1:
            return None
        #- a handful of candidates, not a sweep: column_blockers walks
        #- every track on every layer and a fine-grained scan turned a
        #- 90 s build into a half-hour one, measured
        cands = {ox2, (ox1 + 3 * ox2) // 4, (ox1 + ox2) // 2,
                 (3 * ox1 + ox2) // 4, ox1}
        for c in sorted(cands, reverse=True):
            if int(c) != int(col) and _ok(int(c)):
                return int(c)
    return None


def route_spec(path, tm, claimed=(), router=None, pins=None,
               extent_rects=None):
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

    #- What a claim blocks, computed ONCE and consulted by every shape.
    #- The facing-pins shortcut used to bypass this entirely: a straight
    #- vertical took the overlap's middle whatever the claims said, and
    #- ran through the landing pad a previous net had already spoken
    #- for. A rule the shortcut skips is not a rule.
    span_ys = [n[1] for n in path]
    for _er in (extent_rects or ()):
        span_ys.extend((int(_er.y1), int(_er.y2)))
    span = (min(span_ys), max(span_ys))
    try:
        clear = router.clearance(tm.pin_layer) if router else 0
    except Exception:
        clear = 0

    def taken(x):
        #- a claim is (x, y0, y1) for a trunk, or (x, y0, y1, hw) for
        #- something with its own width -- a routed net's pin, which
        #- will take a LANDING PAD somewhere along itself
        for c in claimed:
            cx, y0, y1 = c[0], c[1], c[2]
            hw = c[3] if len(c) > 3 else 0
            if abs(cx - x) < clear + hw and span[1] > y0 and span[0] < y1:
                return True
        return False

    def free_x_in(lo, hi, want):
        """The free x nearest `want`, in lo..hi, or None."""
        if taken(want) is False:
            return want
        step = max(1, int(getattr(tm, "hpitch", 1)))
        cands = sorted(range(int(lo), int(hi) + 1, step),
                       key=lambda x: abs(x - want))
        for x in cands:
            if not taken(x):
                return x
        return None

    #- A path ALWAYS changes layer, so "is it one layer" is never the
    #- question. The pin layer is pin-only -- a route may via off it and
    #- not run along it -- so the search has to leave it to move at all,
    #- and every pin-to-pin path reads as M1 -> M2 -> ... -> M1.
    #-
    #- What matters is the SHAPE. A path with one x is a vertical, one y
    #- a horizontal, whatever it did about layers on the way.
    opts = ""
    trunk = None

    #- BEFORE anything else: do the two pins simply face each other?
    #-
    #- The search returns a PATH, and a path bends for its own reasons --
    #- it steps off the pin layer to move at all, so it comes back on a
    #- neighbouring track and reads as a bend even when the pins are
    #- squarely in line. Taking the shape from the path therefore asked
    #- route.py for a trunk and branches where a plain vertical would do.
    #-
    #- On an nf=2 device -- source on both sides, drain in the middle --
    #- a series link leaves one drain and lands on the next source with
    #- a wide shared column between them. A straight route down that
    #- overlap is what a person would draw, and it needs no trunk placed
    #- and no lane reserved.
    if pins and len(pins) == 2:
        a, b = pins
        ox1, ox2 = max(a.x1, b.x1), min(a.x2, b.x2)
        oy1, oy2 = max(a.y1, b.y1), min(a.y2, b.y2)
        if ox2 > ox1 and oy2 <= oy1:
            #- share a column, separated vertically
            #- and SAY which column. Left to itself route.py takes the
            #- bar from the net's own rects, which for two offset pins
            #- is their UNION, which is wider than either pin and
            #- reaches whatever sits beside the column. The overlap is
            #- the only part both pins actually share.
            #- the overlap's middle, or the nearest UNCLAIMED lane in
            #- the overlap; a fully claimed overlap is a blocked net,
            #- not a licence
            w2 = clear // 2
            mid = free_x_in(ox1 + w2, ox2 - w2, (ox1 + ox2) // 2)
            if mid is None:
                return None
            #- FALL THROUGH for the layer. This used to return here with
            #- the pin layer, which skipped every check below it -- the
            #- "is the pin layer actually free" test never ran on the
            #- shape that needs it most. That is how the ladder came out
            #- on M1 through a device's own internal metal.
            facing = ("||", f"trunkx={mid}")
        elif oy2 > oy1 and ox2 <= ox1:
            #- share a row, separated horizontally
            facing = ("-", "")
        else:
            facing = None
        if facing is not None:
            rtype, opts = facing
            lane = _pin_layer_if_clear(path, tm, router, pins, None,
                                       extent_rects)
            layer = tm.pin_layer if lane is not None else None
            if lane is not None and rtype == "||":
                opts = f"trunkx={lane}"
            if layer is None:
                on_path = [n[2] for n in path if n[2] != tm.pin_layer]
                want = "v" if rtype == "||" else "h"
                candidates = ([l for l in on_path
                               if tm.directions.get(l) == want]
                              or [l for l, d in tm.directions.items()
                                  if d == want]
                              or on_path)
                if not candidates:
                    return None
                layer = candidates[0]
            return (layer, rtype, opts, None)
    if len(xs) == 1 and len(ys) > 1:
        rtype = "||"
    elif len(ys) == 1 and len(xs) > 1:
        rtype = "-"
    elif len(xs) > 1 and len(ys) > 1:
        #- A bend. route.py draws these as a vertical TRUNK with
        #- horizontal branches off it -- "-|--" puts the trunk left of
        #- the pins, "--|-" right -- which is the same shape a search
        #- returns whenever the two pins share neither row nor column.
        #- Refusing them left every net in a series column unrouted, and
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
        #- ...and not a column another net in this stack is already
        #- using AT THIS HEIGHT. The map is rebuilt per net, but route.py
        #- does not DRAW until after beforeRoute returns, so every search
        #- in a stack sees a column nobody has claimed yet. What the
        #- searches cannot see from each other, the caller remembers.
        #-
        #- A claim is a column AND a y interval, and both halves are
        #- load bearing. A bare set of x was wrong twice over: it kept
        #- a net out of a column its neighbour only used two rows
        #- away, and it let two nets sit half the pitch the metal needs
        #- apart, because that x was, strictly, not the claimed one.
        free = [x for x in by_x if not taken(x)]
        #- NO fallback onto a claimed column. There used to be one --
        #- `or list(by_x)` -- and it turned every full corridor into a
        #- silent short: the claim said the lane was spoken for, and the
        #- route took it anyway. A net that cannot get a clear column is
        #- BLOCKED, which is a truthful answer the caller can act on.
        if not free:
            return None
        trunk = max(free, key=lambda x: (len(by_x[x]), -x))
        rtype = "-|--" if trunk <= (min(xs) + max(xs)) // 2 else "--|-"
        #- and SAY where. Without this route.py places the trunk from
        #- the net's own pins, so five ladder nets in one column each
        #- compute the same lane and land on it: measured, one component
        #- holding every net in the column. The search already picked one
        #- with room in it -- per net, against a map that has the last
        #- route in it -- and trunkx is route.py's way of being told.
        opts = f"trunkx={trunk}"
    else:
        return None

    #- The pin layer when it is clear, else a routing layer that runs
    #- the way this shape needs. _pin_layer_if_clear carries the whole
    #- argument for why that test is shaped as it is.
    vertical = rtype in ("||", "-|--", "--|-")
    want = "v" if vertical else "h"

    lane = _pin_layer_if_clear(path, tm, router, pins, trunk,
                               extent_rects)
    layer = tm.pin_layer if lane is not None else None
    if lane is not None and vertical and lane != trunk:
        #- the clear lane the scan found, not the column the search
        #- happened to walk: route.py must be told or it recomputes
        #- the blocked one from the pins
        trunk = lane
        opts = f"trunkx={lane}"
        if rtype in ("-|--", "--|-"):
            rtype = "-|--" if lane <= (min(xs) + max(xs)) // 2 else "--|-"

    if layer is None:
        on_path = [n[2] for n in path if n[2] != tm.pin_layer]
        candidates = ([l for l in on_path if tm.directions.get(l) == want]
                      or [l for l, d in tm.directions.items() if d == want]
                      or on_path)
        if not candidates:
            return None
        layer = candidates[0]

    if trunk is not None:
        trunk = (trunk, min(n[1] for n in path), max(n[1] for n in path))
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


def draw_supplies_first(layout, log=None):
    """Draw the queued supply routes before anything searches. Returns how many.

    POWER AND GROUND FIRST, and this is what that has to mean
    mechanically. Ordering the list is not enough: a route added in
    beforeRoute is not DRAWN until the routing phase, so a stack search
    running in beforeRoute looks at a column with no strap in it and
    happily routes through one: measured, every net in a series column
    came out shorted to a supply strap the search never saw.

    route() is idempotent only in the sense that nothing calls it twice
    -- LayoutCell.route() skips anything flagged _pre_routed, which is
    the hook this uses. Without the flag the geometry is drawn again in
    the routing phase.

    INCOMPLETE, and measured as such: on a real cell this draws 0.
    The rings and straps do not arrive as Route objects on layout.routes
    -- addRouteRing and addPowerConnection build their geometry another
    way -- so there is nothing here to pre-draw yet. It is not dead
    weight: the queued signal routes it does catch are real, and the
    remaining work is to find where the supply geometry is queued. Until
    then a stack search still cannot see a strap, which is why a stack
    falls back off the pin layer rather than routing around one on it.
    """
    log = log or logging.getLogger("MazeRouter")
    supplies = supply_nets(layout)
    drawn = 0
    for r in getattr(layout, "routes", []):
        if not r.isRoute() or getattr(r, "_pre_routed", False):
            continue
        if getattr(r, "name", "") not in supplies:
            continue
        try:
            r.route()
            r._pre_routed = True
            drawn += 1
        except Exception as e:
            log.warning(f"supply {getattr(r, 'name', '?')}: {e}")
    log.info(f"supplies drawn before stack search: {drawn}")
    return drawn


def _internal_nets(layout, stack):
    """Nets wholly inside `stack` -- one source, shared with the plan.

    Not recomputed here on purpose: the stack cell's port list and the
    set of nets the stack level routes have to be the same set, or the
    layout closes a net the generated subckt still calls a port.
    """
    from .subcell import plan_stack_cells
    for entry in plan_stack_cells(layout):
        if entry["stack"] == stack:
            return set(entry["internal"])
    return set()


def route_stack_level(layout, margin=None, log=None, only=None,
                      boundary=False):
    """Route every net inside every stack. Returns (routed, blocked).

    `margin` is the halo around a stack's own geometry that the search
    is allowed to use. Left as None it comes from the technology --
    two routing pitches, which is the least room a detour around an
    obstacle can possibly need: one pitch to step aside and one to come
    back. It was a literal 8000 for a while, which is that number for
    sky130 and a guess anywhere else.

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
    if margin is None:
        probe = TrackMap(layout)
        margin = 2 * max(probe.hpitch, probe.vpitch)
    routed, blocked = [], []
    #- before ANY search: the straps have to exist to be avoided
    draw_supplies_first(layout, log)
    by_stack = pins_by_stack(layout)
    from .subcell import stack_groups, subcell_spec
    groups = stack_groups(layout)
    #- `only` names the stacks to route. One at a time is the sane way
    #- to bring this up: a stack that is not clean is then the only
    #- thing that can have made the layout dirty, and the next one
    #- starts from a known good state instead of from a pile.
    wanted = None
    if only:
        wanted = {only} if isinstance(only, str) else set(only)
    types = {e["name"]: e["type"] for e in subcell_spec(layout)}
    #- a stack whose own pycell already wired it is finished. Routing it
    #- again lays a second set of wires over the first.
    by_pycell = getattr(layout, "_stacks_routed_by_pycell", None) or set()
    for stack in sorted(by_stack):
        if wanted is not None and stack not in wanted:
            continue
        #- WHICH NETS a stack routes depends on what the stack IS.
        #-
        #- As a region of a flat parent it routes only its INTERNAL
        #- nets. A net with pins outside as well belongs to the level
        #- above: joining the pins that happen to be inside calls the
        #- net done while the rest of it is still elsewhere.
        #-
        #- As a CELL it must route every net it has two or more pins
        #- of, boundary nets included, because a cell that leaves them
        #- apart presents the same net at several ports and hands the
        #- parent a problem it just created. `boundary=True` says the
        #- stack is being built as a cell.
        #-
        #- The old comment here claimed a boundary net could not be
        #- routed inside a series column without shorting the chain.
        #- Measured on the column that produced that claim, with the
        #- devices stacked in chain order: the gate column is clear of
        #- every source and drain pin over the stack's whole height,
        #- and the net routes as a plain vertical. The restriction was
        #- costing closure for nothing.
        internal = _internal_nets(layout, stack)
        pycell_did = stack in by_pycell
        if pycell_did and not boundary:
            log.info(f"{stack}: routed by its own pycell, not searching")
            continue
        #- the TYPE picks the router, and only the stack router exists.
        #- A declared diffpair or mirror wants symmetry or gate bussing
        #- that a series-link search knows nothing about; running it
        #- anyway routes wrongly with a confident log. Decline and say
        #- why -- a pycell routes any type, and takes precedence anyway.
        sc_type = types.get(stack, "stack")
        if sc_type != "stack" and not pycell_did:
            blocked.append((stack, "", f"no {sc_type} router yet; "
                            f"ship a {stack} pycell or retype it"))
            log.warning(f"{stack}: declared type={sc_type}, and only the "
                        f"stack router exists; not routing")
            continue
        subs = {n: rs for n, rs in by_stack[stack].items()
                if len(rs) >= 2 and (n in internal or boundary)}
        if pycell_did:
            #- its pycell has already spoken for the internal nets;
            #- the boundary nets are still ours
            subs = {n: rs for n, rs in subs.items() if n not in internal}
        if not subs:
            continue
        from .subcell import stack_membership
        insts_in_stack = sorted({n for n, st in stack_membership(layout).items()
                                 if st == stack})
        allr = [r for v in by_stack[stack].values() for r in v]
        extent = (min(r.x1 for r in allr) - margin,
                  min(r.y1 for r in allr) - margin,
                  max(r.x2 for r in allr) + margin,
                  max(r.y2 for r in allr) + margin)
        claimed = set()
        #- THE PARENT'S QUEUED ROUTES CLAIM THEIR LANDINGS TOO. A route
        #- the top level created in its own beforeRoute is not drawn yet
        #- -- nothing is, that is this flow's original sin -- so the
        #- stack search cannot see the pad it will drop on a pin inside
        #- this very stack. Measured: the top's power-up route lands on
        #- a gate in the load column, and the stack's drain trunk chose
        #- exactly that x. The route object knows its rects; claim them,
        #- tagged by net so a net does not block itself.
        preclaims = []
        for ro in getattr(layout, "routes", []) or []:
            rnet = getattr(ro, "net", "") or ""
            for rr in (list(getattr(ro, "startRects", []) or [])
                       + list(getattr(ro, "stopRects", []) or [])):
                if rr is None:
                    continue
                if (rr.x2 < extent[0] or rr.x1 > extent[2]
                        or rr.y2 < extent[1] or rr.y1 > extent[3]):
                    continue
                preclaims.append((rnet,
                                  (int((rr.x1 + rr.x2) // 2),
                                   int(rr.y1) - margin,
                                   int(rr.y2) + margin,
                                   int((rr.x2 - rr.x1) // 2 + margin // 2))))
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
                #- No routeMirror fast path. It was tried for gate nets and
                #- it DREW NOTHING while reporting success -- the
                #- excludeNets narrowing starves it of the context its
                #- decline logic feeds on, and a "routed" that draws
                #- nothing is this flow's oldest lie. The lane fast path
                #- below covers the all-gate net on the tab centre.
                #- FAST PATH 2: a single-terminal net whose lane column
                #- is clear does not need the search at all. The search
                #- was only consulted for a shape, and on a crowded
                #- column it returns a staircase and the net was blocked
                #- for it -- while the lane, which never staircases, sat
                #- unused because it only applied to search-shaped
                #- verticals.
                lane0 = _terminal_lane(rects, tm.pin_layer, "||")
                if lane0 is not None:
                    ys0 = ([int(rr.y1) for rr in rects]
                           + [int(rr.y2) for rr in rects])
                    try:
                        pad0 = Rules.getInstance().get(tm.pin_layer,
                                                       "space")
                    except Exception:
                        pad0 = 0
                    ok = False
                    try:
                        ok = (tm.column_blockers(
                                  net, lane0 - pad0, lane0 + pad0,
                                  min(ys0), max(ys0)) == []
                              and tm.column_metal(
                                  net, tm.pin_layer,
                                  lane0 - pad0, lane0 + pad0,
                                  min(ys0), max(ys0)) == [])
                    except Exception:
                        ok = False
                    if ok:
                        grp = groups.get(stack)
                        if grp is None:
                            raise Blocked(
                                f"no group object for stack {stack}")
                        grp.addConnectivityRoute(
                            tm.pin_layer, f"^{re.escape(net)}$", "||",
                            f"trunkx={lane0}", 1)
                        claimed.add((lane0, min(ys0), max(ys0)))
                        routed.append((stack, net))
                        continue
                #- Search for the shape, then hand it to route.py. The
                #- search proves a path exists and says which layer and
                #- direction it wants; the drawing is not ours to do.
                specs = []
                other_claims = claimed | {c for n2, c in preclaims
                                          if n2 != net}
                for a, b in zip(rects, rects[1:]):
                    layer = getattr(a, "layer", None) or tm.pin_layer
                    start = (*r.pin_centre(a), layer)
                    goal = (*r.pin_centre(b), layer)
                    r._own = [a, b]
                    path = r.search(start, goal,
                                    r.manhattan_heuristic(r.snap(goal)))
                    spec = route_spec(path, tm, other_claims, r, (a, b),
                                      extent_rects=rects)
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
                #- the lane the terminal owns beats the lane the search
                #- found: left edge for a source net, right edge for a
                #- drain net. The search still proved a path exists.
                lane = _terminal_lane(rects, layer, rtype)
                if lane is not None and claimed:
                    #- a lane is a convention, not a right of way: if a
                    #- routed net's pin or trunk already spans it, the
                    #- searched column stands
                    _ys = ([int(rr.y1) for rr in rects]
                           + [int(rr.y2) for rr in rects])
                    _lo, _hi = min(_ys), max(_ys)
                    _cl = r.clearance(tm.pin_layer)
                    for c in claimed:
                        hw = c[3] if len(c) > 3 else 0
                        if (abs(c[0] - lane) < _cl + hw
                                and _hi > c[1] and _lo < c[2]):
                            lane = None
                            break
                if lane is not None:
                    opts = f"trunkx={lane}"
                    ys_all = ([int(r.y1) for r in rects]
                              + [int(r.y2) for r in rects])
                    trunk = (lane, min(ys_all), max(ys_all))
                    #- AND ON THE PIN LAYER, if the lane's own column is
                    #- clear. The whole point of an edge lane is that it
                    #- runs where nothing else lives -- the drain bars
                    #- start well right of the source lane, the gate
                    #- tabs right of the drain lane -- so the wire can
                    #- stay on the metal its pins are already on: no
                    #- via, no landing pad, no cut enclosure to spill
                    #- onto a neighbour. The earlier whole-pin-span test
                    #- said no here because the span holds the device's
                    #- own rails; the LANE column does not.
                    if layer != tm.pin_layer and tm.pin_layer:
                        try:
                            pad = Rules.getInstance().get(tm.pin_layer,
                                                          "space")
                        except Exception:
                            pad = 0
                        lo, hi = min(ys_all), max(ys_all)
                        try:
                            clear = (tm.column_blockers(
                                         net, lane - pad, lane + pad,
                                         lo, hi) == []
                                     and tm.column_metal(
                                         net, tm.pin_layer,
                                         lane - pad, lane + pad,
                                         lo, hi) == [])
                        except Exception:
                            clear = False
                        if clear:
                            layer = tm.pin_layer
                #- A STRAIGHT VERTICAL'S TRUNK LIES INSIDE EVERY PIN IT
                #- LANDS ON. route.py drops each landing pad at the
                #- trunk's x; a trunk outside a pin's span slides the
                #- pad clean off the pin -- measured, a pad 11000 past
                #- its own pin's edge, sitting on the neighbour's gate
                #- tab instead. The common overlap of all the pins is
                #- where a straight vertical may run; a net whose pins
                #- share no column is not a straight vertical, whatever
                #- the shape of the searched path.
                if rtype == "||":
                    ox1 = max(int(rr.x1) for rr in rects)
                    ox2 = min(int(rr.x2) for rr in rects)
                    m2 = re.search(r"trunkx=(-?[0-9.]+)", opts or "")
                    tx = int(float(m2.group(1))) if m2 else None
                    #- the WIRE must lie on every pin: half its width,
                    #- not half a clearance -- the edge lanes sit half a
                    #- width in from the pin edge by construction, and a
                    #- clearance-sized margin blocked every one of them
                    w2 = r.rule(tm.pin_layer, "width") // 2
                    if ox2 - ox1 < 2 * w2:
                        raise Blocked(
                            f"{net}: pins share only {ox2 - ox1} of "
                            f"column, a straight vertical cannot land")
                    if tx is None or tx < ox1 + w2 or tx > ox2 - w2:
                        raise Blocked(
                            f"{net}: trunk {tx} lies outside the pins' "
                            f"common overlap {ox1}..{ox2}")
                    #- and if the route needs a VIA at each pin, the
                    #- smallest cut must FIT the narrowest pin. A 3800
                    #- pad on a 3200 gate tab overhangs 300 a side
                    #- whatever the placement -- measured, six li
                    #- spacing errors that no shifting can remove.
                    if layer != tm.pin_layer:
                        try:
                            w_cut = r.via_extent(tm.pin_layer, layer)[0]
                        except Exception:
                            w_cut = 0
                        narrow = min(int(rr.x2 - rr.x1) for rr in rects)
                        if w_cut and narrow < w_cut:
                            raise Blocked(
                                f"{net}: narrowest pin is {narrow} and "
                                f"the smallest {tm.pin_layer}-{layer} "
                                f"pad is {w_cut}; it overhangs whatever "
                                f"the placement")
                if trunk is not None:
                    claimed.add(trunk)
                grp = groups.get(stack)
                if grp is None:
                    raise Blocked(f"no group object for stack {stack}")
                grp.addConnectivityRoute(layer, f"^{re.escape(net)}$",
                                         rtype, opts, 1)
                #- CLAIM THE LANDINGS, not only the trunk. A routed net
                #- will drop a via pad somewhere on each of its pins,
                #- and none of it is drawn until the phase ends, so the
                #- next net's trunk sails through the spot: measured, a
                #- trunk chosen at the exact x where the previous net's
                #- pad landed on its own pin, pad on wire, one short.
                #- Each pin is claimed across its width plus half a pad,
                #- for the pad's own height around it.
                if layer != tm.pin_layer:
                    pad_w = int(r.via_cost)
                    for pr in rects:
                        claimed.add((int((pr.x1 + pr.x2) // 2),
                                     int(pr.y1) - pad_w,
                                     int(pr.y2) + pad_w,
                                     int((pr.x2 - pr.x1) // 2 + pad_w // 2)))
                routed.append((stack, net))
            except Blocked as e:
                blocked.append((stack, net, str(e)))
                log.warning(f"{stack}/{net}: {e}")
    return routed, blocked




#- ---------------------------------------------------------------------
#- The subcell-publication family lives in subcell.py now. Design
#- pycells in the wild still import it from here -- and their failure
#- mode is brutal: run_stack_pycells swallows the ImportError, reports
#- the stack unhandled, and the cell simply loses its routes. Forward
#- instead of breaking.
_MOVED_TO_SUBCELL = {
    "subcell_spec", "subcell_membership", "stack_membership",
    "subcell_groups", "stack_groups", "plan_subcells",
    "plan_stack_cells", "stack_subckt", "design_of",
    "run_stack_pycells", "write_stack_cells",
}


def __getattr__(name):
    if name in _MOVED_TO_SUBCELL:
        from . import subcell
        return getattr(subcell, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
