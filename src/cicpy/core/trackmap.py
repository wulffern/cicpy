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

#- the reserved owner of device-internal metal: not a net, never equal
#- to one, so it blocks every net alike
DEVICE_METAL = "!device"

from .rules import Rules
from .layer import Layer


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
        #- net -> list of (lo, hi). `spans` merges a net down to one
        #- min/max, which is fine for "is this track busy" and wrong for
        #- "is THIS interval busy": a net appearing at two distant places
        #- on one track then appears to occupy everything between them.
        #- Measured -- using the merged extent to check via columns
        #- blocked every via off every pin in the switch column.
        self.wires = defaultdict(list)

    def occupy(self, net, lo, hi):
        span = self.spans[net]
        span[0] = lo if span[0] is None else min(span[0], lo)
        span[1] = hi if span[1] is None else max(span[1], hi)
        self.wires[net].append((lo, hi))

    #- Geometry with no net. `_collectPhysicalRects` cannot resolve a
    #- rect inside an instance to a net -- only PORTS are attributable,
    #- through the node graph -- so a device's internal rails all arrive
    #- as "?". Treating that as foreign blocks a via off every pin by
    #- the pin's OWN metal, which is what it did: every ladder net came
    #- back "no path", explored 1 node.
    #-
    #- So unattributed metal does not block. The cost is real and worth
    #- stating: a via can land on a device's internal rail without this
    #- noticing. It is bounded, because the electrically interesting M1
    #- in a device IS its ports, and those are attributed and checked as
    #- pins. Closing it properly means attributing instance geometry,
    #- which is the same job as step 2b was for pins.
    UNATTRIBUTED = ("", "?", None)
    #- set from the technology by TrackMap; the class default is only
    #- what a Track built outside one would use
    TOLERATE_UNATTRIBUTED_ON = ()

    def foreign_spans(self, net, lo, hi, tolerate_unattributed=None):
        """Spans in lo..hi that do not belong to `net`.

        `tolerate_unattributed` defaults to the layer rule; pass False to
        see unattributed metal too. A caller that knows which of it is
        its OWN -- a route holds the pin rects it is joining -- can then
        filter, which is the only way to allow a via on a pin without
        also allowing one on the device rail beside it.
        """
        if tolerate_unattributed is None:
            tolerate_unattributed = self.layer in self.TOLERATE_UNATTRIBUTED_ON
        out = []
        for other, spans in self.wires.items():
            if other == net:
                continue
            if other in self.UNATTRIBUTED and tolerate_unattributed:
                continue
            for a, b in spans:
                if not (hi <= a or lo >= b):
                    out.append((other, a, b))
        return out

    def wire_overlaps(self, net, lo, hi, tolerate_unattributed=None):
        """Foreign wire actually inside lo..hi on this track."""
        return bool(self.foreign_spans(net, lo, hi, tolerate_unattributed))

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

    #- Nothing about the stack is written down here. The technology
    #- knows its own layers, their order and which way each runs; a
    #- router that hard codes "M1 is the pin layer" or "M3 is
    #- horizontal" is a sky130 router wearing a general name.
    #-   ROUTE.pinlayer    which layer carries pins
    #-   ROUTE.directions  preferred direction per routing layer
    #-   layer previous/next chain   order and via adjacency
    #- Only the last of the three was already in the tech file.

    def __init__(self, layout, directions=None, extent=None, scope=None,
                 block_pins=False):
        """
        ``scope`` restricts the map to one subtree -- a CellGroup, a
        stack, a single instance -- instead of the whole cell.

        This is the difference between "which tracks are free" and
        "which tracks are free *for this piece of work*". Planning a
        route against every rect in the design is what makes a router
        fight geometry it can never touch: measured, a top level query
        reported 0 horizontal tracks free across a mid channel because
        one trunk crossed all of them, while the span the net actually
        needed had 27.
        """
        self.log = logging.getLogger("TrackMap")
        self.layout = layout
        self.scope = scope
        self.rules = Rules.getInstance()
        self.block_pins = block_pins
        self.pin_layer = self._route_str("pinlayer")
        self.directions = dict(directions or self._tech_directions())
        #- ROUTE.pintravel is the technology saying the pin layer may
        #- be TRAVELLED, and which way. Without it the pin layer is
        #- pin-only: it joins the map so pins can be modelled, but no
        #- search may run along it.
        self.pin_travel = self._route_str("pintravel")
        if self.pin_travel not in ("h", "v"):
            self.pin_travel = ""
        if block_pins and self.pin_layer:
            #- the pin layer joins the map when pins are modelled: it is
            #- not routed on unless pintravel says so, but it is where
            #- every pin is
            self.directions.setdefault(self.pin_layer,
                                       self.pin_travel
                                       or self._pin_layer_direction())
        self.hpitch = int(self._rule("ROUTE", "horizontalgrid", 3000))
        self.vpitch = int(self._rule("ROUTE", "verticalgrid", 4000))
        self.extent = extent
        self.tracks = {}

    def _route_raw(self, key, default=None):
        try:
            route = self.rules.getValue("rules", "ROUTE")
        except Exception:
            return default
        return route.get(key, default) if isinstance(route, dict) else default

    def _route_str(self, key, default=""):
        v = self._route_raw(key, default)
        return v if isinstance(v, str) else default

    def _tech_directions(self):
        d = self._route_raw("directions")
        if isinstance(d, dict) and d:
            return dict(d)
        self.log.warning(
            "ROUTE.directions missing from the technology; no layer has a "
            "preferred direction and nothing can be routed")
        return {}

    def _pin_layer_direction(self):
        """Which way the pin layer runs, taken from the stack.

        The pin layer is pin-only, so it has no ROUTE.directions entry
        of its own -- but it still needs one here, because that is what
        decides whether a pin is bucketed into tracks along x or along
        y, and bucketing it the wrong way puts every pin on one track.

        A metal stack alternates, so the answer is the opposite of the
        first routing layer above the pin layer. Hard coding "h" was a
        sky130 answer wearing a general name: it is right for M1 here
        and wrong the moment a technology runs its bottom metal the
        other way.
        """
        stack = self.metal_stack()
        if self.pin_layer in stack:
            for layer in stack[stack.index(self.pin_layer) + 1:]:
                d = self.directions.get(layer)
                if d:
                    return "v" if d == "h" else "h"
        #- nothing above it in the stack has a direction: fall back to
        #- the opposite of whatever the technology does have, so the
        #- pins at least do not share an axis with the only routing
        #- layer there is
        for d in self.directions.values():
            return "v" if d == "h" else "h"
        return "h"

    def layer_cost(self, layer):
        """The relative price of travelling on `layer`, from ROUTE.costs.

        The technology says what it wants used: here the pin layer is
        the cheapest, so a search prefers it wherever its corridors are
        clear, and the attributed device metal is what keeps that
        honest. A layer the tech does not price costs the default 2 --
        more than a priced pin layer, less than a discouraged one.
        """
        costs = self._route_raw("costs")
        if isinstance(costs, dict) and layer in costs:
            try:
                return max(1, int(costs[layer]))
            except (TypeError, ValueError):
                pass
        return 2

    def metal_stack(self):
        """Metal layers in stack order, from the tech's own chain.

        Follows previous/next (M1 -> VIA1 -> M2 -> ...) rather than
        sorting names. Sorting happened to work for M1..M5 and would
        put M10 between M1 and M2 the moment a technology had one.
        """
        layers = getattr(self.rules, "layers", None) or {}
        metals, byname = {}, {}
        for name in layers:
            try:
                l = self.rules.getLayer(name)
            except Exception:
                continue
            byname[name] = l
            if getattr(l, "material", None) == Layer.metal:
                metals[name] = l
        if not metals:
            return []
        starts = [n for n, l in metals.items()
                  if getattr(l, "previous", "") not in metals
                  and getattr(l, "previous", "") not in
                  {getattr(m, "previous", "") for m in metals.values()
                   if False}]
        #- the bottom metal is the one nothing leads into
        incoming = set()
        for n, l in metals.items():
            via = getattr(l, "next", "")
            for m, ml in metals.items():
                if getattr(ml, "previous", "") == via:
                    incoming.add(m)
        starts = [n for n in metals if n not in incoming] or [sorted(metals)[0]]
        order, seen = [], set()
        cur = starts[0]
        while cur and cur not in seen:
            order.append(cur)
            seen.add(cur)
            via = getattr(metals[cur], "next", "")
            cur = next((m for m, ml in metals.items()
                        if getattr(ml, "previous", "") == via), None)
        return order

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

        tolerate = (self.pin_layer,) if self.pin_layer else ()
        for layer, direction in self.directions.items():
            horizontal = direction == "h"
            pitch = self.vpitch if horizontal else self.hpitch
            lo, hi = (y1, y2) if horizontal else (x1, x2)
            n = max(1, int((hi - lo) // pitch) + 1)
            self.tracks[layer] = []
            for i in range(n):
                t = Track(i, lo + i * pitch, layer, horizontal)
                t.TOLERATE_UNATTRIBUTED_ON = tolerate
                self.tracks[layer].append(t)

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
            span_lo = r.x1 if horizontal else r.y1
            span_hi = r.x2 if horizontal else r.y2
            #- DEVICE METAL IS A PIN OF NOBODY. A rect inside an
            #- instance that coincides with none of its pins belongs to
            #- no net and may not be crossed, landed on, or tolerated:
            #- it is blocked under a name no net can ever equal. This
            #- replaces "unattributed, so tolerated", which is the hole
            #- a via pad fell through on five of eight subcells.
            if getattr(r, "device_metal", False):
                for i in range(first, last + 1):
                    self.tracks[layer][i].block(DEVICE_METAL, span_lo, span_hi)
                continue
            net = getattr(r, "net", "") or "?"
            for i in range(first, last + 1):
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

        Verified against a measured short: the net dropping a via
        column into a resistor over the full height of the row returns
        the one foreign pin in its way, which is the pin the short
        report blamed.

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

    def column_metal(self, net, layer, x1, x2, y1, y2):
        """Metal in the column that is not `net`'s, INCLUDING unattributed.

        `column_blockers` answers with PINS, and a pin is all it can
        answer with: `_collectPhysicalRects` cannot resolve a rect
        inside an instance to a net, so a device's own internal rails
        arrive as "?" and are tolerated everywhere on the pin layer.
        That tolerance is what makes the router usable at all -- treat
        "?" as foreign and every via off every pin is blocked by the
        pin's own metal.

        It is also a hole, and a series column fell through it. A
        transistor cell may carry an unattributed strip on the pin layer
        up its side, past both S and D, and in a compact library those
        two pins sit a few hundred nanometres apart and overlap in x. A
        route drawn on the PIN LAYER between one device's D and the next
        device's S then ties D to S through that strip: measured, magic
        extracted a six device chain with D and S as one node, while the
        connectivity check here -- which tolerates the strip -- reported
        it only after the flood relabelled it.

        So: staying on the pin layer is safe only where there is no
        foreign metal AT ALL in the corridor, attributed or not. Ask
        this before choosing it; ask `column_blockers` for the ordinary
        "is another net's pin in the way" question.

        Returns [(net_or_"?", coord, span_lo, span_hi)].
        """
        out = []
        horizontal = self.directions.get(layer) == "h"
        lo, hi = (y1, y2) if horizontal else (x1, x2)
        a, b = (x1, x2) if horizontal else (y1, y2)
        for t in self.tracks.get(layer, []):
            if not (lo <= t.coord <= hi):
                continue
            for other, s0, s1 in t.foreign_spans(net, a, b,
                                                 tolerate_unattributed=False):
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
