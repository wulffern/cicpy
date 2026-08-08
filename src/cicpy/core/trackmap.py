"""What is where: the occupancy of the cell's routing tracks.

The problem this solves
-----------------------

A route is placed with a track number, and the number is an offset from
*the net's own pins*::

    trunk_x = anchor_right + (track + 1) * vspace + track * vwidth
    base_y  = min(rect.centerY() for rect in self.accessRects)

So two nets whose pins sit in the same column compute nearly the same
anchor and land on top of each other at the same track number. Neither
knows the other exists. The only way to find that out is to draw it and
read the short report, which means the way to route a crowded cell is to
guess, regenerate, and read: a minute a guess, and thirty guesses is an
evening.

This module answers the question directly instead. Tracks are numbered
once for the whole cell, and every track says which nets already occupy
it and over what span. "Which corridor is free between these two rows"
becomes a lookup rather than an experiment.

It reads geometry that already exists, so it works on any cell: a design
mid-route, or one finished years ago whose channel budget nobody wrote
down.
"""

import logging
from collections import defaultdict

from .rules import Rules


class Track:
    """One routing track, and who is on it."""

    def __init__(self, index, coord, layer, horizontal):
        self.index = index
        self.coord = coord
        self.layer = layer
        self.horizontal = horizontal
        #- net -> (min, max) along the track
        self.spans = defaultdict(lambda: [None, None])

    def occupy(self, net, lo, hi):
        span = self.spans[net]
        span[0] = lo if span[0] is None else min(span[0], lo)
        span[1] = hi if span[1] is None else max(span[1], hi)

    @property
    def nets(self):
        return sorted(self.spans)

    @property
    def free(self):
        return not self.spans

    def occupied_length(self):
        return sum((hi - lo) for lo, hi in self.spans.values()
                   if lo is not None and hi is not None)

    def __repr__(self):
        return f"Track({self.layer} {self.index} @{self.coord} {self.nets})"


class TrackMap:
    """Number the cell's tracks once, and record what sits on each.

    ``horizontal`` layers are cut into tracks along y, ``vertical``
    layers along x, at the ROUTE pitch for that direction. Which layer
    runs which way is the house convention and can be overridden.
    """

    DEFAULT_DIRECTIONS = {"M2": "v", "M3": "h", "M4": "v", "M5": "h"}

    def __init__(self, layout, directions=None, extent=None, scope=None):
        """
        ``scope`` restricts the map to one subtree -- a CellGroup, a
        stack, a single instance -- instead of the whole cell.

        This is the difference between "which tracks are free" and
        "which tracks are free *for this piece of work*". Planning a
        route against every rect in the design is what makes a router
        fight geometry it can never touch: measured on LELOTEMP_OTAR, a
        top level query reports 0 M3 tracks free across the mid channel
        because one trunk crosses all of them, while the span a given
        net actually needs has 27.
        """
        self.log = logging.getLogger("TrackMap")
        self.layout = layout
        self.scope = scope
        self.rules = Rules.getInstance()
        self.directions = dict(directions or self.DEFAULT_DIRECTIONS)
        self.hpitch = int(self._rule("ROUTE", "horizontalgrid", 3000))
        self.vpitch = int(self._rule("ROUTE", "verticalgrid", 4000))
        self.extent = extent
        self.tracks = {}

    def _rule(self, layer, key, default):
        try:
            return self.rules.get(layer, key)
        except Exception:
            return default

    def build(self):
        #- _collectPhysicalRects already walks an arbitrary subtree, so
        #- scoping costs one argument
        rects = [r for r in self.layout._collectPhysicalRects(self.scope)
                 if getattr(r, "layer", "") in self.directions]
        if not rects:
            self.log.warning("no geometry on any routing layer")
            return self

        if self.extent:
            x1, y1, x2, y2 = self.extent
        else:
            x1 = min(r.x1 for r in rects)
            y1 = min(r.y1 for r in rects)
            x2 = max(r.x2 for r in rects)
            y2 = max(r.y2 for r in rects)
        self.extent = (x1, y1, x2, y2)

        for layer, direction in self.directions.items():
            horizontal = direction == "h"
            pitch = self.vpitch if horizontal else self.hpitch
            lo, hi = (y1, y2) if horizontal else (x1, x2)
            n = max(1, int((hi - lo) // pitch) + 1)
            self.tracks[layer] = [
                Track(i, lo + i * pitch, layer, horizontal) for i in range(n)
            ]

        for r in rects:
            layer = r.layer
            horizontal = self.directions[layer] == "h"
            pitch = self.vpitch if horizontal else self.hpitch
            lo, hi = (y1, y2) if horizontal else (x1, x2)
            #- a wire covers every track its width crosses
            a = r.y1 if horizontal else r.x1
            b = r.y2 if horizontal else r.x2
            first = max(0, int((a - lo) // pitch))
            last = min(len(self.tracks[layer]) - 1, int((b - lo) // pitch))
            net = getattr(r, "net", "") or "?"
            for i in range(first, last + 1):
                span_lo = r.x1 if horizontal else r.y1
                span_hi = r.x2 if horizontal else r.y2
                self.tracks[layer][i].occupy(net, span_lo, span_hi)
        return self

    #-----------------------------------------------------------------
    #- questions worth asking
    #-----------------------------------------------------------------

    def free_tracks(self, layer, lo=None, hi=None):
        """Track indices with nothing on them, optionally within a band."""
        out = []
        for t in self.tracks.get(layer, ()):
            if lo is not None and t.coord < lo:
                continue
            if hi is not None and t.coord > hi:
                continue
            if t.free:
                out.append(t.index)
        return out

    def free_between(self, layer, span_lo, span_hi, lo=None, hi=None):
        """Tracks free *over a given span*, which is the real question.

        A channel track carrying one short wire at the far left is still
        usable on the right. Asking only for wholly empty tracks throws
        away most of the budget.
        """
        out = []
        for t in self.tracks.get(layer, ()):
            if lo is not None and t.coord < lo:
                continue
            if hi is not None and t.coord > hi:
                continue
            clash = False
            for net, (a, b) in t.spans.items():
                if a is None:
                    continue
                if a < span_hi and b > span_lo:
                    clash = True
                    break
            if not clash:
                out.append(t.index)
        return out

    def track_at(self, layer, coord):
        best = None
        for t in self.tracks.get(layer, ()):
            if best is None or abs(t.coord - coord) < abs(best.coord - coord):
                best = t
        return best

    def report(self, layer=None, band=None, verbose=False):
        """A human and model readable picture of the routing budget."""
        lines = []
        x1, y1, x2, y2 = self.extent or (0, 0, 0, 0)
        lines.append(
            f"track map over ({x1},{y1})-({x2},{y2}), "
            f"h pitch {self.hpitch}, v pitch {self.vpitch}")
        for lname in sorted(self.tracks):
            if layer and lname != layer:
                continue
            tracks = self.tracks[lname]
            horizontal = self.directions[lname] == "h"
            shown = [t for t in tracks
                     if band is None or (band[0] <= t.coord <= band[1])]
            used = [t for t in shown if not t.free]
            lines.append(
                f"{lname} {'horizontal' if horizontal else 'vertical'}: "
                f"{len(shown)} tracks, {len(used)} used, "
                f"{len(shown) - len(used)} free")
            for t in shown:
                if t.free and not verbose:
                    continue
                nets = ", ".join(
                    f"{n}[{int(a)}..{int(b)}]" for n, (a, b) in
                    sorted(t.spans.items()) if a is not None)
                lines.append(f"   t{t.index:<3d} @{int(t.coord):<8d} {nets}")
        return "\n".join(lines)
