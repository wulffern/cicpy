"""A route as a STORY: anchored steps, spelled `~`.

The maze search finds a polyline and `route_spec` (core/mazerouter.py)
then has to squash it into one of route.py's eleven canned shapes plus
an absolute `trunkx`. When it fits none of them the net is ABANDONED --
which is what every ``("net", "blocked", "not a shape route.py can
draw")`` in a design file is. A polyline is the native form of what the
search already produces, so nothing needs squashing and nothing is
abandoned::

    p = cell.path("VBP", "M1")
    p.start()                       # the matched start rects, as they are
    p.up()                          # via to the next layer up
    p.movex(p.tab_lane())           # over to the gate-tab lane
    p.trunk()                       # ride it the length of the pins
    p.down()                        # back down to the pin layer
    p.end()                         # and land on the stop rects

Every call appends a step and returns the path, so a chain works too --
but one call per line is what should be written and generated: the
router regenerates these, and a step per line diffs as one changed line
where a chained expression diffs as the whole route.

THREE RULES THE STEPS ENFORCE, so a design cannot break them:

* **the ends are PORTS.** `start()` and `end()` take the route's own
  start/stop rects and use them where they are. Ports are not on any
  grid and are not made to be.
* **no coordinates.** An anchor names something in the design -- a pin,
  a port, a tab lane, a channel track -- and an offset is counted in
  `PITCH` (width + space, one legal lane) or `SPACE` (the minimum gap),
  both read from the technology. There is no way to write a nanometre.
* **no 1x1 vias.** A layer change places the largest cut that fits
  (`_fittedCut`), which prefers 2x2, 1x2, 2x1 in that order.

THE VOCABULARY IS OPEN. A step is a small class with one method --
given the run so far, extend it -- registered by name. A new construct
is a new class beside the others and touches nothing central; an
unknown name raises at parse time rather than drawing something
plausible.
"""
import logging

from .rect import Rect, HorizontalRectangleFromTo, VerticalRectangleFromTo
from .route import Route
from .rules import Rules

log = logging.getLogger("Path")


#- ------------------------------------------------------------------
#- units: a length is a count of rule-derived lanes, never a number
#- ------------------------------------------------------------------

class Unit:
    """A per-layer length from the technology. `2 * p.PITCH` is two
    legal lanes; there is deliberately no way to say "6000"."""

    def __init__(self, rule):
        self.rule = rule
        self.count = 1

    def _scaled(self, n):
        u = Unit(self.rule)
        u.count = self.count * n
        return u

    def __rmul__(self, n):
        return self._scaled(n)

    def __mul__(self, n):
        return self._scaled(n)

    def __neg__(self):
        return self._scaled(-1)

    def resolve(self, layer):
        rules = Rules.getInstance()
        if self.rule == "pitch":
            base = rules.get(layer, "width") + rules.get(layer, "space")
        else:
            base = rules.get(layer, self.rule)
        return int(self.count * base)


#- ------------------------------------------------------------------
#- anchors: a coordinate named by something that is in the design
#- ------------------------------------------------------------------

class Anchor:
    """Resolves to a coordinate against a path. Subclass and register."""

    axis = "x"

    def __init__(self):
        self.offset = None

    def __add__(self, unit):
        import copy
        a = copy.copy(self)
        a.offset = unit if self.offset is None else self.offset
        return a

    def __sub__(self, unit):
        return self.__add__(-unit)

    def coord(self, path):
        raise NotImplementedError

    def resolve(self, path):
        c = self.coord(path)
        if c is None:
            return None
        if self.offset is not None:
            c += self.offset.resolve(path.routeLayer)
        return int(c)


class _PinAnchor(Anchor):
    """The centre of one instance's terminal. The pin IS the spec."""

    def __init__(self, instance, terminal, axis="x"):
        super().__init__()
        self.instance = instance
        self.terminal = terminal
        self.axis = axis

    def coord(self, path):
        r = path.instanceTerminalRect(self.instance, self.terminal)
        if r is None:
            log.error(f"{path.net}: no terminal {self.terminal} on "
                      f"{self.instance}")
            return None
        return r.centerX() if self.axis == "x" else r.centerY()


class _TrunkAnchor(Anchor):
    """One of the pin-derived lanes route.py already resolves:
    `trunktab`, `trunkright`, `trunkleft` (see Route.trunkAnchors)."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind

    def coord(self, path):
        return path.trunkAnchors().get(self.kind)


class _TrackAnchor(Anchor):
    """A track inside a named routing channel. The fallback for when no
    pin anchor says it -- an index means the same relative position
    whatever the technology makes the pitch."""

    def __init__(self, channel, index):
        super().__init__()
        self.channel = channel
        self.index = index

    def coord(self, path):
        cell = path.cell()
        if cell is None:
            log.error(f"{path.net}: a track anchor needs the cell")
            return None
        return cell.channelTrackCoord(self.channel, self.index)


#- ------------------------------------------------------------------
#- steps: given the run so far, extend it
#- ------------------------------------------------------------------

STEPS = {}


def step(cls):
    """Register a step under its `name`. That is the whole extension
    mechanism -- there is no dispatch table to edit."""
    STEPS[cls.name] = cls
    return cls


class Step:
    name = ""

    def apply(self, path, cur):
        """Extend the run. `cur` is (x, y, layer); return the new one."""
        raise NotImplementedError

    def astuple(self):
        return (self.name,)


@step
class Start(Step):
    """Begin ON THE PORT, wherever the port is."""
    name = "start"

    def apply(self, path, cur):
        r = path.anchorRect(path.startRects)
        if r is None:
            return cur
        return (int(r.centerX()), int(r.centerY()), r.layer)


@step
class End(Step):
    """Land ON THE PORT. Draws whatever leg is still needed to reach it."""
    name = "end"

    def apply(self, path, cur):
        r = path.anchorRect(path.stopRects)
        if r is None:
            return cur
        x, y, layer = cur
        tx, ty = int(r.centerX()), int(r.centerY())
        if x != tx:
            path.drawSegment(x, y, tx, y, layer)
        if y != ty:
            path.drawSegment(tx, y, tx, ty, layer)
        if layer != r.layer:
            path.drawVia(tx, ty, layer, r.layer)
        return (tx, ty, r.layer)


@step
class Up(Step):
    """One layer up the technology's own chain, or to a named one."""
    name = "up"
    direction = "next"

    def __init__(self, layer=None):
        self.layer = layer

    def apply(self, path, cur):
        x, y, layer = cur
        target = self.layer or path.neighbourLayer(layer, self.direction)
        if target is None or target == layer:
            log.warning(f"{path.net}: no layer {self.direction} of {layer}")
            return cur
        path.drawVia(x, y, layer, target)
        return (x, y, target)

    def astuple(self):
        return (self.name,) if self.layer is None else (self.name, self.layer)


@step
class Down(Up):
    name = "down"
    direction = "previous"


@step
class MoveX(Step):
    """A horizontal leg to an anchored x."""
    name = "movex"
    axis = "x"

    def __init__(self, anchor):
        self.anchor = anchor

    def apply(self, path, cur):
        x, y, layer = cur
        c = path.resolveAnchor(self.anchor)
        if c is None:
            return cur
        if self.axis == "x":
            path.drawSegment(x, y, c, y, layer)
            return (c, y, layer)
        path.drawSegment(x, y, x, c, layer)
        return (x, c, layer)

    def astuple(self):
        return (self.name, repr(self.anchor))


@step
class MoveY(MoveX):
    name = "movey"
    axis = "y"


@step
class Trunk(Step):
    """Ride a lane the length of the route's own pins.

    The workhorse: of 19 trunks measured across the two hierarchical
    designs, 10 were exactly a pin anchor and 7 more within a fraction
    of a wire width of one.
    """
    name = "trunk"

    def __init__(self, at=None, direction="v"):
        self.at = at
        self.direction = direction

    def apply(self, path, cur):
        x, y, layer = cur
        rects = [r for r in (path.startRects + path.stopRects)
                 if r is not None]
        if not rects:
            return cur
        c = x if self.at is None else path.resolveAnchor(self.at)
        if c is None:
            return cur
        if self.direction == "v":
            lo = min(int(r.y1) for r in rects)
            hi = max(int(r.y2) for r in rects)
            if c != x:
                path.drawSegment(x, y, c, y, layer)
            path.drawSegment(c, lo, c, hi, layer)
            return (c, y, layer)
        lo = min(int(r.x1) for r in rects)
        hi = max(int(r.x2) for r in rects)
        if c != y:
            path.drawSegment(x, y, x, c, layer)
        path.drawSegment(lo, c, hi, c, layer)
        return (x, c, layer)

    def astuple(self):
        return (self.name, self.direction, repr(self.at))


#- ------------------------------------------------------------------
#- the path itself
#- ------------------------------------------------------------------

class Path(Route):
    """A Route whose shape is a list of steps rather than one of eleven
    names.

    Subclassing Route is not tidiness: `isType` walks the MRO, so a Path
    answers `isRoute()` True, and that is what makes
    `LayoutCell.route()` draw it at all and what makes the connectivity
    flood attribute its via cuts to its net. An object that merely
    quacked like a route would be built, added, and silently never
    drawn.
    """

    def __init__(self, net, layer, start=None, stop=None, options=""):
        Route.__init__(self, net, layer, start or [], stop or [],
                       options, "~")
        self.routeType = "POLYLINE"
        self.steps = []
        self.layoutcell = None

    #- units, on the path so a design imports one name
    PITCH = Unit("pitch")
    SPACE = Unit("space")

    #- -- anchors ---------------------------------------------------
    def pin(self, instance, terminal, axis="x"):
        return _PinAnchor(instance, terminal, axis)

    def tab_lane(self):
        return _TrunkAnchor("trunktab")

    def right_of_pins(self):
        return _TrunkAnchor("trunkright")

    def left_of_pins(self):
        return _TrunkAnchor("trunkleft")

    def track(self, channel, index):
        return _TrackAnchor(channel, index)

    #- -- steps -----------------------------------------------------
    def _add(self, s):
        self.steps.append(s)
        return self

    def start(self):
        return self._add(Start())

    def end(self):
        return self._add(End())

    def up(self, layer=None):
        return self._add(Up(layer))

    def down(self, layer=None):
        return self._add(Down(layer))

    def movex(self, anchor):
        return self._add(MoveX(anchor))

    def movey(self, anchor):
        return self._add(MoveY(anchor))

    def trunk(self, at=None, direction="v"):
        return self._add(Trunk(at, direction))

    #- -- what the steps use ----------------------------------------
    def cell(self):
        if self.layoutcell is not None:
            return self.layoutcell
        p = getattr(self, "parent", None)
        seen = set()
        while p is not None and id(p) not in seen:
            seen.add(id(p))
            if hasattr(p, "channelTrackCoord"):
                return p
            p = getattr(p, "parent", None)
        return None

    def anchorRect(self, rects):
        live = [r for r in rects if r is not None]
        return live[0] if live else None

    def instanceTerminalRect(self, instance, terminal):
        cell = self.cell()
        if cell is None:
            return None
        inst = cell.getInstanceFromInstanceName(instance)
        if inst is None:
            return None
        port = (getattr(inst, "instancePorts", {}) or {}).get(terminal)
        return port.get() if port is not None else None

    def resolveAnchor(self, anchor):
        if anchor is None:
            return None
        if isinstance(anchor, Anchor):
            return anchor.resolve(self)
        log.error(f"{self.net}: {anchor!r} is not an anchor. A step takes "
                  f"something named in the design, never a coordinate.")
        return None

    def neighbourLayer(self, layer, direction):
        rules = Rules.getInstance()
        lay = rules.getLayer(layer) if rules is not None else None
        if lay is None:
            return None
        #- the technology's own chain names the CUT between two metals,
        #- so step twice: metal -> cut -> metal
        cut = getattr(lay, direction, "")
        cl = rules.getLayer(cut) if cut else None
        if cl is None:
            return None
        return getattr(cl, direction, "") or None

    def drawSegment(self, x1, y1, x2, y2, layer):
        w = Rules.getInstance().get(layer, self.routeWidthRule)
        if y1 == y2:
            r = HorizontalRectangleFromTo(layer, x1, x2, y1 - w // 2, w)
        elif x1 == x2:
            r = VerticalRectangleFromTo(layer, x1 - w // 2, y1, y2, w)
        else:
            log.error(f"{self.net}: a step asked for a diagonal from "
                      f"({x1},{y1}) to ({x2},{y2})")
            return None
        r.setNet(self.net)
        self.add(r)
        return r

    def viaArray(self, fromLayer, toLayer):
        """The cut array to use between two layers.

        Largest first: a 1x1 is not good enough for reliability, so it
        is the last thing tried and never the first. Both layer orders
        and both orientations, because a technology names the cut from
        one side only.
        """
        from .cut import Cut
        wanted = [(self.cuts, self.vcuts), (2, 2), (1, 2), (2, 1), (1, 1)]
        seen = set()
        for h, v in wanted:
            if (h, v) in seen:
                continue
            seen.add((h, v))
            for a, b in ((fromLayer, toLayer), (toLayer, fromLayer)):
                for hh, vv in ((h, v), (v, h)):
                    ct = Cut.getInstance(a, b, hh, vv)
                    if ct is not None:
                        return ct
        return None

    def drawVia(self, x, y, fromLayer, toLayer):
        if fromLayer == toLayer:
            return None
        cut = self.viaArray(fromLayer, toLayer)
        if cut is None:
            log.error(f"{self.net}: no cut between {fromLayer} and "
                      f"{toLayer}")
            return None
        cut.moveCenter(int(x), int(y))
        self.add(cut)
        return cut

    #- -- drawing ---------------------------------------------------
    def route(self):
        """Walk the steps. The one override Route needs."""
        self.log.info(f"path: net={self.net}, layer={self.routeLayer}, "
                      f"steps={len(self.steps)}")
        if not self.steps:
            self.log.warning(f"{self.net}: a path with no steps draws "
                             f"nothing")
            return
        cur = (0, 0, self.routeLayer)
        for s in self.steps:
            cur = s.apply(self, cur)

    def astuples(self):
        """The story as the serialised form the router emits."""
        return [s.astuple() for s in self.steps]
