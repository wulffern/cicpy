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
        #- net -> list of (lo, hi) pin spans. Kept apart from `spans`
        #- because they answer a different question: a wire of another
        #- net is something to avoid overlapping, a PIN of another net
        #- is something no route may cross at all.
        self.pins = defaultdict(list)

    def occupy(self, net, lo, hi):
        span = self.spans[net]
        span[0] = lo if span[0] is None else min(span[0], lo)
        span[1] = hi if span[1] is None else max(span[1], hi)

    def block(self, net, lo, hi):
        self.pins[net].append((lo, hi))

    def blocking(self, net):
        """Spans on this track that `net` may not cross: every other
        net's pins."""
        return [s for n, spans in self.pins.items() if n != net for s in spans]

    def crosses_pin(self, net, lo, hi):
        """True if a wire of `net` from lo..hi would run over a foreign pin."""
        return any(not (hi <= a or lo >= b) for a, b in self.blocking(net))

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
    #- M1 is not a routing layer here -- it is the pin layer, and the
    #- house rule reserves it for power. It still has to be in the map
    #- when pins are being modelled, because that is where every pin
    #- is: measured on LELOTEMP_OTAR, all 213 of them.
    PIN_DIRECTIONS = {"M1": "h"}

    def __init__(self, layout, directions=None, extent=None, scope=None,
                 block_pins=False):
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
        self.block_pins = block_pins
        self.directions = dict(directions or self.DEFAULT_DIRECTIONS)
        if block_pins:
            for k, v in self.PIN_DIRECTIONS.items():
                self.directions.setdefault(k, v)
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
        if self.block_pins:
            self._mark_pins()
        return self

    def _mark_pins(self):
        x1, y1, x2, y2 = self.extent
        for net, r in self._pin_rects():
            layer = getattr(r, "layer", "")
            if layer not in self.tracks:
                continue
            horizontal = self.directions[layer] == "h"
            pitch = self.vpitch if horizontal else self.hpitch
            lo = y1 if horizontal else x1
            a = r.y1 if horizontal else r.x1
            b = r.y2 if horizontal else r.x2
            first = max(0, int((a - lo) // pitch))
            last = min(len(self.tracks[layer]) - 1, int((b - lo) // pitch))
            span_lo = r.x1 if horizontal else r.y1
            span_hi = r.x2 if horizontal else r.y2
            for i in range(first, last + 1):
                self.tracks[layer][i].block(net, span_lo, span_hi)

    def _pin_rects(self):
        """(net, rect) for every pin, with the net resolved properly.

        NOT from the port's own name. A subcell's port is called B or S
        or P in its own cell and that says nothing about which net the
        instance terminal is wired to -- attributing pins that way gives
        cell-local names and a router that compares the wrong things.

        The node graph already holds the answer: nodeGraph[net].ports is
        the ports of that net, which is the same source
        _directNodeAccessRects routes from. Reading pins from there
        means the map and the router agree by construction.
        """
        graphs = getattr(self.layout, "nodeGraph", None)
        if not graphs:
            self.log.warning("no node graph; pins cannot be attributed to nets")
            return
        for net in getattr(self.layout, "nodeGraphList", []) or list(graphs):
            g = graphs.get(net)
            if g is None:
                continue
            for port in getattr(g, "ports", []):
                for layer in self.directions:
                    rr = port.get(layer) if hasattr(port, "get") else None
                    if rr is not None:
                        yield net, rr

    def column_blockers(self, net, x1, x2, y1, y2):
        """Foreign pins inside the via column (x1..x2) over y1..y2.

        This, not same-layer overlap, is the test that matters. A trunk
        on M4 and a pin on M1 never share a track, so `crosses_pin` on
        either layer reports nothing -- measured, it rejected 0 of 3
        candidate tracks for the one collision known to exist. What
        actually collides is the VIA COLUMN: a route reaching a pin has
        to come down through every layer at that x, and any other net's
        pin in the way is shorted.

        Verified against LELOTEMP_OTAR's VS/VDS failure: VS dropping at
        x 265200..274200 over y 57300..290700 returns VDS at y 104000,
        which is the pin the short report blamed.

        Returns [(net, y, x1, x2)].
        """
        out = []
        for layer, direction in self.directions.items():
            horizontal = direction == "h"
            for t in self.tracks.get(layer, []):
                #- the coordinate the track sits at must be inside the
                #- span the column travels through
                lo, hi = (y1, y2) if horizontal else (x1, x2)
                if not (lo <= t.coord <= hi):
                    continue
                a, b = (x1, x2) if horizontal else (y1, y2)
                for other, spans in t.pins.items():
                    if other == net:
                        continue
                    for s0, s1 in spans:
                        if not (b <= s0 or a >= s1):
                            out.append((other, int(t.coord), int(s0), int(s1)))
        return out

    def free_for(self, net, layer, span_lo, span_hi, lo=None, hi=None):
        """Track indices `net` can use over span_lo..span_hi.

        Stricter than `free_between`: a track is rejected if it carries
        another net at all, and also if crossing it would run over
        another net's PIN. The second test is the one the old router
        could not make -- every OTAR failure was a trunk laid through a
        pin that nothing was looking at.
        """
        out = []
        for i in self.free_between(layer, span_lo, span_hi, lo, hi):
            if not self.tracks[layer][i].crosses_pin(net, span_lo, span_hi):
                out.append(i)
        return out

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
