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
    VIA_PAD_FALLBACK = 4000

    #- M1 is the pin layer here and the house rule reserves it for
    #- power, so a route may via OFF a pin on it but never run ALONG it.
    #- Without this the search tries to walk M1 through the pins of
    #- every net in the column and gets nowhere.
    PIN_ONLY_LAYERS = ("M1",)

    def __init__(self, trackmap, net, via_cost=None, log=None):
        self.tm = trackmap
        self.net = net
        #- default: a via costs what it physically occupies. Not a tuned
        #- constant -- if a detour is shorter than the pad it displaces,
        #- the detour genuinely is cheaper.
        self._via_size = {}
        self.via_cost = (self.via_extent("M2", "M3")[0]
                         if via_cost is None else via_cost)
        self.log = log or logging.getLogger("MazeRouter")
        self._layers = sorted(self.tm.directions)
        self._adj = self._layer_adjacency()
        self._pin_index = self._index_foreign_pins()

    #-----------------------------------------------------------------
    #- the grid
    #-----------------------------------------------------------------

    def _layer_adjacency(self):
        """Which layers a via may connect.

        Neighbours in the routing stack, by name order (M1,M2,...). The
        stack is what the technology's connect rules say; using name
        order here keeps the router honest about only stepping one layer
        at a time, which is what makes the M1..M5 stack expensive rather
        than free -- and an M1..M5 stack is what failed via3.1 when it
        was taken in one go.
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

    def is_free(self, track, lo, hi):
        """Can this net occupy `track` from lo..hi?

        Two questions, and the second is the one that matters: is the
        span clear of other nets' wire, and would occupying it cross
        another net's pin.

        Takes the Track rather than an index: TrackMap.track_at returns
        the object, and converting back to an index was a bug waiting to
        be written.
        """
        if track is None:
            return False
        if track.wire_overlaps(self.net, lo, hi):
            return False
        return not track.crosses_pin(self.net, lo, hi)

    def _via_layers(self, a_layer, b_layer):
        """The layers a via between a_layer and b_layer occupies."""
        try:
            i, j = self._layers.index(a_layer), self._layers.index(b_layer)
        except ValueError:
            return dict(self.tm.directions)
        lo, hi = sorted((i, j))
        return {l: self.tm.directions[l] for l in self._layers[lo:hi + 1]
                if l in self.tm.directions}

    def via_extent(self, a_layer, b_layer):
        """(width, height) of the real cut between two layers."""
        key = tuple(sorted((a_layer, b_layer)))
        if key not in self._via_size:
            try:
                from cicpy.core.cut import Cut
                inst = Cut.getInstance(a_layer, b_layer, 1, 1)
                self._via_size[key] = (int(inst.width()), int(inst.height()))
            except Exception:
                self._via_size[key] = (self.VIA_PAD_FALLBACK,
                                       self.VIA_PAD_FALLBACK)
        return self._via_size[key]

    def via_is_free(self, x, y, a_layer=None, b_layer=None):
        """Can this net drop a via column at (x, y)?

        The column is the cut's real size and claims every layer, so this is
        where two nets most often collide -- and it is exactly what
        `column_blockers` was built to answer.
        """
        w, h = self.via_extent(a_layer or "M2", b_layer or "M3")
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
            for t in self.tm.tracks.get(layer, []):
                if not (lo <= t.coord <= hi):
                    continue
                if t.wire_overlaps(self.net, a, b):
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
        for delta in () if layer in self.PIN_ONLY_LAYERS else (-step, step):
            nx, ny = (x + delta, y) if horizontal else (x, y + delta)
            if not self.in_bounds(nx, ny):
                continue
            track = self.tm.track_at(layer, y if horizontal else x)
            if track is None:
                continue
            lo, hi = sorted(((x, nx) if horizontal else (y, ny)))
            if self.is_free(track, lo, hi):
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
                #- a layer change ends the run and makes a via
                if (start[0], start[1]) != (prev[0], prev[1]) or start is path[0]:
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

    def connect(self, layout, a_rect, b_rect, layer="M1", width=None):
        """Search between two pin rects and draw the result.

        The convenience the pycells want: give it two pins, get geometry
        or a Blocked with a reason. Deliberately explicit about WHICH
        two pins -- picking them automatically needs the connectivity
        components, and guessing them is how a router quietly adds a
        redundant route that shorts something.
        """
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
        w = width or self.tm.hpitch
        half = w // 2
        nrect = 0
        for layer, x1, y1, x2, y2 in runs:
            lx, hx = sorted((x1, x2))
            ly, hy = sorted((y1, y2))
            if lx == hx:
                lx, hx = lx - half, hx + half
            if ly == hy:
                ly, hy = ly - half, hy + half
            #- built directly rather than through addRectangle so the
            #- NET can be set. Without it the rect comes back as "?" on
            #- the next map rebuild and the router cannot tell its own
            #- earlier geometry from a foreign net's.
            rr = Rect(layer, int(lx), int(ly), int(hx - lx), int(hy - ly))
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
