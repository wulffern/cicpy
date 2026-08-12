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
import os

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

    def toJson(self):
        return {"rule": self.rule, "count": self.count}

    @staticmethod
    def fromJson(o):
        if not o:
            return None
        u = Unit(o.get("rule", "pitch"))
        u.count = o.get("count", 1)
        return u

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

    #- ROUND TRIP. `astuple` renders an anchor with repr() for a human
    #- to read in a wires block; that is not a form anything can read
    #- back, so a path written to a .cic came home as geometry with no
    #- story. These two are the machine form.
    anchor_kind = ""

    def toJson(self):
        o = {"kind": self.anchor_kind, "axis": self.axis}
        if self.offset is not None:
            o["offset"] = self.offset.toJson()
        o.update(self._json())
        return o

    def _json(self):
        return {}

    @staticmethod
    def fromJson(o):
        if not o:
            return None
        cls = ANCHORS.get(o.get("kind", ""))
        if cls is None:
            log.error(f"unknown anchor {o.get('kind')!r} in a path")
            return None
        a = cls._make(o)
        if a is None:
            return None
        a.axis = o.get("axis", a.axis)
        a.offset = Unit.fromJson(o.get("offset"))
        return a


class _PinAnchor(Anchor):
    anchor_kind = "pin"

    @classmethod
    def _make(cls, o):
        return cls(o.get("instance", ""), o.get("terminal", ""), o.get("axis", "x"))

    def _json(self):
        return {"instance": self.instance, "terminal": self.terminal}

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


    def __repr__(self):
        return f"pin({self.instance}.{self.terminal}.{self.axis})"

class _LandingAnchor(Anchor):
    anchor_kind = "landing"

    @classmethod
    def _make(cls, o):
        return cls(o.get("axis", "y"))

    def _json(self):
        return {}

    """Where this path ENDS, on either axis.

    `end()` lands on the stop rect, so a story that has to arrive on a
    row before it travels along it needs to name that row -- and the
    only honest name for it is the landing itself. A pin anchor cannot
    serve: `instanceTerminalRect` keys on the NET, so a net with two
    pins on one instance (a loop: LPO back to LPI) resolves to
    whichever the port dict happens to hold.
    """

    def __init__(self, axis="y"):
        super().__init__()
        self.axis = axis

    def coord(self, path):
        r = path.anchorRect(path.stopRects)
        if r is None:
            log.error(f"{path.net}: a landing anchor needs stop rects")
            return None
        return r.centerX() if self.axis == "x" else r.centerY()


    def __repr__(self):
        return f"landing({self.axis})"

class _TrunkAnchor(Anchor):
    anchor_kind = "trunk"

    @classmethod
    def _make(cls, o):
        return cls(o.get("trunk", ""))

    def _json(self):
        return {"trunk": self.kind}

    """One of the pin-derived lanes route.py already resolves:
    `trunktab`, `trunkright`, `trunkleft` (see Route.trunkAnchors)."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind

    def coord(self, path):
        return path.trunkAnchors().get(self.kind)


    def __repr__(self):
        return f"{self.kind}"

class _FixedAnchor(Anchor):
    anchor_kind = "fixed"

    @classmethod
    def _make(cls, o):
        return cls(o.get("value", 0), o.get("axis", "x"))

    def _json(self):
        return {"value": self.value}

    """A resolved coordinate. THE TOOLS' FORM, never a design's.

    route.py has said it for years: "trunkx is the resolved form and
    belongs to the tools, not to a pycell". The search works in
    coordinates and must be able to draw what it found; what it may not
    do is write one into a design file. `is_fixed` is how the wires
    writer tells the difference and refuses.
    """

    is_fixed = True

    def __init__(self, value, axis="x"):
        super().__init__()
        self.value = int(value)
        self.axis = axis

    def coord(self, path):
        return self.value

    def __repr__(self):
        return f"fixed({self.value})"


class _TrackAnchor(Anchor):
    anchor_kind = "track"

    @classmethod
    def _make(cls, o):
        return cls(o.get("channel", ""), o.get("index", 0))

    def _json(self):
        return {"channel": self.channel, "index": self.index}

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

    def __repr__(self):
        return f"track({self.channel},{self.index})"


#- every anchor by its tag, so a serialised one can be rebuilt
ANCHORS = {c.anchor_kind: c for c in
           (_PinAnchor, _LandingAnchor, _TrunkAnchor, _FixedAnchor,
            _TrackAnchor)}


#- ------------------------------------------------------------------
#- steps: given the run so far, extend it
#- ------------------------------------------------------------------

STEPS = {}


def step(cls):
    """Register a step under its `name`. That is the whole extension
    mechanism -- there is no dispatch table to edit."""
    STEPS[cls.name] = cls
    return cls


    def __repr__(self):
        return f"track({self.channel},{self.index})"

class Step:
    name = ""

    def apply(self, path, cur):
        """Extend the run. `cur` is (x, y, layer); return the new one."""
        raise NotImplementedError

    def astuple(self):
        return (self.name,)

    def toJson(self):
        o = {"step": self.name}
        o.update(self._json())
        return o

    def _json(self):
        return {}

    @classmethod
    def _make(cls, o):
        return cls()


@step
class Start(Step):
    """Begin ON THE PORT, wherever the port is.

    A step carries its OWN rect when it is given one. The steps run at
    route time, long after they are built, so a leg that read the
    path's startRects then would see whatever they had become -- and a
    net drawn as several legs would anchor every one of them to the
    same pin. Measured: eight of ten pins never landed on, three
    devices and three nets missing at LVS.
    """
    name = "start"

    def __init__(self, rect=None):
        self.rect = rect

    def apply(self, path, cur):
        r = self.rect if self.rect is not None else \
            path.anchorRect(path.startRects)
        if r is None:
            return cur
        return (int(r.centerX()), int(r.centerY()), r.layer)


@step
class End(Step):
    """Land ON THE PORT. Draws whatever leg is still needed to reach it."""
    name = "end"

    def __init__(self, rect=None):
        self.rect = rect

    def apply(self, path, cur):
        r = self.rect if self.rect is not None else \
            path.anchorRect(path.stopRects)
        if r is None:
            return cur
        x, y, layer = cur
        tx, ty = int(r.centerX()), int(r.centerY())
        if x is None or y is None:
            #- nothing to travel from: land on the stop and stop
            x, y = tx, ty
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

    def _json(self):
        return {"layer": self.layer}

    @classmethod
    def _make(cls, o):
        return cls(o.get("layer"))

    def apply(self, path, cur):
        x, y, layer = cur
        target = self.layer or path.neighbourLayer(layer, self.direction)
        if target is None or target == layer:
            log.warning(f"{path.net}: no layer {self.direction} of {layer}")
            return cur
        if x is None or y is None:
            #- a via needs a place to be; a story that changes layer
            #- before it has gone anywhere says where first
            log.warning(f"{path.net}: {self.name} before the path has "
                        f"a position; no via placed")
            return (x, y, target)
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
            if y is None:
                return (c, y, layer)
            path.drawSegment(x, y, c, y, layer)
            return (c, y, layer)
        if x is None:
            return (x, c, layer)
        path.drawSegment(x, y, x, c, layer)
        return (x, c, layer)

    def _json(self):
        return {"anchor": self.anchor.toJson()
                if isinstance(self.anchor, Anchor) else None}

    @classmethod
    def _make(cls, o):
        return cls(Anchor.fromJson(o.get("anchor")))

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
        rects = path.allRects()
        if not rects:
            return cur
        c = x if self.at is None else path.resolveAnchor(self.at)
        if c is None:
            return cur
        if self.direction == "v":
            lo = min(int(r.y1) for r in rects)
            hi = max(int(r.y2) for r in rects)
            if x is not None and y is not None and c != x:
                path.drawSegment(x, y, c, y, layer)
            path.drawSegment(c, lo, c, hi, layer, extend=False)
            return (c, y, layer)
        lo = min(int(r.x1) for r in rects)
        hi = max(int(r.x2) for r in rects)
        if x is not None and y is not None and c != y:
            path.drawSegment(x, y, x, c, layer)
        path.drawSegment(lo, c, hi, c, layer)
        return (x, c, layer)

    def _json(self):
        return {"direction": self.direction,
                "at": self.at.toJson() if isinstance(self.at, Anchor) else None}

    @classmethod
    def _make(cls, o):
        return cls(Anchor.fromJson(o.get("at")), o.get("direction", "v"))

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
        #- `Route.__init__` sets `self.track = 0` for the `trackN`
        #- option, and an instance attribute SHADOWS the class method
        #- of the same name -- so `p.track(channel, index)`, the one
        #- anchor that names a channel lane, raised "'int' object is
        #- not callable" and had never worked. Every read of
        #- Route.track is inside routeOne/routeVertical/routeU, which a
        #- POLYLINE never enters (Path overrides route()), so dropping
        #- the attribute costs nothing and gives the anchor back.
        if not self.hasTrack:
            del self.track

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

    def landing(self, axis="y"):
        return _LandingAnchor(axis)

    #- -- steps -----------------------------------------------------
    def _add(self, s):
        self.steps.append(s)
        return self

    def start(self, rect=None):
        return self._add(Start(rect))

    def end(self, rect=None):
        return self._add(End(rect))

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

    def comb(self, at=None, direction="v"):
        return self._add(Comb(at, direction))

    def merge(self, at=None, direction="right"):
        return self._add(Merge(at, direction))

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

    def allRects(self):
        """Every pin this path is scoped to, start and stop alike.

        A merge or a trunk serves the whole scope; only start() and
        end() care which end a rect is.
        """
        return [r for r in (self.startRects + self.stopRects)
                if r is not None]

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

    def drawSegment(self, x1, y1, x2, y2, layer, extend=True):
        """One leg, drawn CORNER TO CORNER rather than end to end.

        A polyline drawn as abutting rects leaves a notch at every turn
        -- the two legs meet at a point, so the outer corner is a
        square of nothing and the inner one is a sliver. Both are
        minimum-width errors, and a leg shorter than the wire width is
        one all by itself. Extending each leg half a width past its
        endpoint makes consecutive legs OVERLAP squarely, which is what
        a corner is, and puts a floor under the length of a short one.
        This is the detail `route_spec` warns about: "emitting raw rects
        and cut instances instead reimplements that badly... 272 DRC
        errors of minimum width, minimum area and via enclosure".
        """
        w = Rules.getInstance().get(layer, self.routeWidthRule)
        #- `half` centres the wire on its own centreline, always.
        #-
        #- `ext` fills the CORNER, and only the ARRIVING leg needs it.
        #- Take a leg coming from the left into a corner P where the
        #- next leg goes up: the horizontal covers the corner square's
        #- left half, the vertical covers its top half, and the
        #- bottom-right quadrant is a notch -- a minimum-width error.
        #- Extending the arriving leg half a width past P fills exactly
        #- that. Extending BOTH ends of BOTH legs also fills it, and
        #- puts metal where the search reserved no clearance: measured
        #- on VD1, four spacing errors at 0.03um where 0.14 is wanted.
        #- A span ends where it says it ends, as `||` does.
        #- ON GRID BEFORE ANYTHING IS BUILT. An anchor may land between
        #- grid steps through no fault of its own: `Start` opens at the
        #- start rect's CENTRE, and a pin whose width is not an even
        #- number of steps has a centre that is not on one. Measured --
        #- LELO_TEMP's VC pin, 84550..960000, centre 522275, which the
        #- magic writer rejects outright ("not a multiple of 50
        #- database units"). Snapping here covers every step at once,
        #- because every step ends up drawing through this.
        x1, x2, y1, y2 = (self._snap(v) for v in (x1, x2, y1, y2))
        half = w // 2
        ext = half if extend else 0
        if y1 == y2 and x1 != x2:
            if x2 > x1:
                lo, hi = x1, x2 + ext
            else:
                lo, hi = x2 - ext, x1
            r = HorizontalRectangleFromTo(layer, lo, hi, y1 - half, w)
        elif x1 == x2 and y1 != y2:
            if y2 > y1:
                lo, hi = y1, y2 + ext
            else:
                lo, hi = y2 - ext, y1
            r = VerticalRectangleFromTo(layer, x1 - half, lo, hi, w)
        elif x1 == x2 and y1 == y2:
            return None
        else:
            log.error(f"{self.net}: a step asked for a diagonal from "
                      f"({x1},{y1}) to ({x2},{y2})")
            return None
        r.setNet(self.net)
        self.add(r)
        return r

    def _snap(self, v):
        """A coordinate on the technology's own grid step.

        The step comes from the tech file, never from a constant here:
        a design that writes 5 nm and one that writes 1 nm are the same
        code. A tech with no grid to answer to snaps to nothing.
        """
        if v is None:
            return v
        try:
            from .gridcheck import gridFromRules
            g = gridFromRules(Rules.getInstance())
        except Exception:
            g = 0
        if not g:
            return int(v)
        return int(round(float(v) / g) * g)

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
        #- NO POSITION YET, which is not the same as the origin. A
        #- story that opens with a trunk has nothing to travel FROM,
        #- and (0,0) made it travel from the coordinate origin: a leg
        #- the width of the whole cell, drawn on the pin layer, at
        #- y=0. It went unseen while a subcell was COPIED out of a
        #- parent -- the leg started outside the copied window and was
        #- left behind -- and appeared the moment subcells were built
        #- from their own origin, as two li spacing errors in
        #- LELOTEMP_OTAR_N_LOAD_A. Every step that travels checks for
        #- it and simply starts where it is told instead.
        cur = (None, None, self.routeLayer)
        for s in self.steps:
            cur = s.apply(self, cur)
        #- NOT by default. mergeOwnRects removes real redundancy --
        #- 28 rects of one ten-pin net -- but doing so costs
        #- connectivity: with it on, LVS goes from "Circuits match
        #- uniquely" to "Netlists do not match", and why a shape wholly
        #- inside another should matter is not yet understood. Set
        #- CICPY_PATH_MERGE=1 to investigate.
        if os.environ.get("CICPY_PATH_MERGE"):
            self.mergeOwnRects()

    def mergeOwnRects(self):
        """Drop this path's own redundant metal.

        A net with N pins is drawn as N-1 stories, and consecutive
        stories share most of their route -- the same lane, a few units
        apart. Two shapes of ONE net that overlap are not a short, but
        two that ALMOST overlap are a notch, and a notch is a
        minimum-spacing error like any other. So a rect wholly inside
        another goes, and two that overlap on the same centreline
        become one.
        """
        rects = [c for c in list(self.children)
                 if hasattr(c, "isRect") and c.isRect()]
        drop = set()
        for i, a in enumerate(rects):
            if i in drop:
                continue
            for j, b in enumerate(rects):
                if i == j or j in drop or a.layer != b.layer:
                    continue
                #- b inside a
                if (b.x1 >= a.x1 and b.x2 <= a.x2
                        and b.y1 >= a.y1 and b.y2 <= a.y2):
                    drop.add(j)
                    continue
                #- CONTAINMENT ONLY. Growing `a` to swallow an
                #- overlapping neighbour also works and takes DRC one
                #- lower, but it MUTATES a rect other things may already
                #- be holding -- port placement reads the net's own
                #- geometry -- and that came back as a failed pin match.
                #- Removing a shape that is wholly inside another
                #- changes no geometry at all, so it cannot.
        if not drop:
            return
        for idx in sorted(drop, reverse=True):
            try:
                self.children.remove(rects[idx])
            except ValueError:
                pass
        log.info(f"{self.net}: merged {len(drop)} redundant rects")

    def astuples(self):
        """The story as the serialised form the router emits."""
        return [s.astuple() for s in self.steps]

    def toJson(self):
        """The drawn geometry AND the story that made it.

        A path used to serialise as its children alone, so a .cic held
        the wire and not the reasoning -- and the reader had no case for
        the class at all, which meant even the wire was dropped. Both
        halves belong in the file: the steps are what a tool regenerates
        or re-reads, the children are what a viewer draws.
        """
        o = super().toJson()
        o["class"] = "Path"
        o["net"] = self.net
        o["routeLayer"] = self.routeLayer
        o["options"] = self.options
        o["steps"] = [st.toJson() for st in self.steps]
        return o

    def fromJson(self, o):
        super().fromJson(o)
        #- Cell.fromJson reads no children, so a Path read its own
        #- metal as nothing. The dispatch that LayoutCell uses is
        #- shared for exactly this.
        from .layoutcell import readJsonChildren
        readJsonChildren(self, o)
        self.net = o.get("net", self.net)
        self.routeLayer = o.get("routeLayer", self.routeLayer)
        self.options = o.get("options", self.options)
        self.routeType = "POLYLINE"
        self.route_ = "~"
        self.steps = []
        for so in o.get("steps") or []:
            cls = STEPS.get(so.get("step", ""))
            if cls is None:
                log.error(f"{self.net}: unknown step {so.get('step')!r}")
                continue
            st = cls._make(so)
            if st is not None:
                self.steps.append(st)
        return self

    def isResolved(self):
        """Does any step still carry a coordinate?

        A resolved path may be DRAWN but must not be written into a
        design: the wires writer asks this and records the net as
        searched-not-declared instead of pasting a number.
        """
        for s in self.steps:
            a = getattr(s, "anchor", None) or getattr(s, "at", None)
            if getattr(a, "is_fixed", False):
                return True
        return False

    #- -- from a searched path --------------------------------------
    def fromNodes(self, nodes, a=None, b=None):
        """Take the shape the maze search actually found.

        The search returns a node per grid step, so a path that turns
        twice can be forty-seven nodes long -- `route_spec`'s own
        comment says the count is an artefact: "a path bends for its
        own reasons... and reads as a bend even when the pins are
        squarely in line". What matters is the CORNERS, so collinear
        runs collapse first. Emitting a rect per node instead is what
        produced "272 DRC errors of minimum width, minimum area and via
        enclosure" the last time someone bypassed route.py.
        """
        corners = simplify(nodes)
        if len(corners) < 2:
            return self
        self.start(a)
        cur = corners[0]
        for nxt in corners[1:]:
            if nxt[2] != cur[2]:
                self._add(_LayerTo(nxt[2]))
            if nxt[0] != cur[0]:
                self.movex(_FixedAnchor(nxt[0]))
            if nxt[1] != cur[1]:
                self.movey(_FixedAnchor(nxt[1], "y"))
            cur = nxt
        self.end(b)
        return self


@step
class Merge(Step):
    """Bring every pin sideways onto one lane, ON THIS LAYER.

    The step that stops a router going up and down. A net whose pins do
    not share a column can still be one rail if the pins are first
    brought to a common lane -- and the way to do that is a leg per pin
    on the layer they are already on, not a via per pin to hop over the
    device and back.

    Pair it with `trunk` at the same anchor: merge lays the legs, trunk
    lays the rail they meet on. That is the two-line story behind

        conn("M1", "^VD1$", "||", "trunktab", 1, "", r"^(xnd1|xnd3)$")

    and it is why the hand-written version has no vias in it at all.
    """
    name = "merge"

    def __init__(self, at=None, direction="right"):
        self.at = at
        self.direction = direction

    def apply(self, path, cur):
        rects = path.allRects()
        if not rects:
            return cur
        c = path.resolveAnchor(self.at)
        if c is None:
            log.error(f"{path.net}: merge needs a lane to merge onto")
            return cur
        layer = path.routeLayer
        for r in rects:
            y = int(r.centerY())
            #- from the pin EDGE facing the lane, so the leg is as
            #- short as it can be and still start on its own pin
            if c >= int(r.x2):
                x = int(r.x2)
            elif c <= int(r.x1):
                x = int(r.x1)
            else:
                continue        # the lane already crosses this pin
            path.drawSegment(x, y, c, y, layer)
        return (c, cur[1], layer)

    def _json(self):
        return {"direction": self.direction,
                "at": self.at.toJson() if isinstance(self.at, Anchor) else None}

    @classmethod
    def _make(cls, o):
        return cls(Anchor.fromJson(o.get("at")), o.get("direction", "v"))

    def astuple(self):
        return (self.name, self.direction, repr(self.at))


@step
class Comb(Step):
    """One trunk, and a stub from every pin to it.

    What a person draws for a multi-pin net, and what the hand-written
    hooks in the designs are: `conn("M1", "^VD1$", "||", "trunkright")`
    is a trunk on the pins' right edge with a landing on each. A chain
    of pair-to-pair paths reaches the same nets and draws nine
    overlapping routes to do it -- measured on VD1, ten pins, nine
    chains, four DRC errors that the two rails it replaced did not have.

    The trunk needs no pin to sit on, which is the point: it serves
    pins that share NO common column, where no straight vertical can
    land and the canned `||` gives up.
    """
    name = "comb"

    def __init__(self, at=None, direction="v"):
        self.at = at
        self.direction = direction

    def apply(self, path, cur):
        rects = path.allRects()
        if not rects:
            return cur
        c = path.resolveAnchor(self.at) if self.at is not None else None
        if c is None:
            return cur
        layer = path.routeLayer
        if self.direction == "v":
            for r in rects:
                path.drawSegment(int(r.centerX()), int(r.centerY()),
                                 c, int(r.centerY()), layer)
            lo = min(int(r.centerY()) for r in rects)
            hi = max(int(r.centerY()) for r in rects)
            path.drawSegment(c, lo, c, hi, layer, extend=False)
            return (c, hi, layer)
        for r in rects:
            path.drawSegment(int(r.centerX()), int(r.centerY()),
                             int(r.centerX()), c, layer)
        lo = min(int(r.centerX()) for r in rects)
        hi = max(int(r.centerX()) for r in rects)
        path.drawSegment(lo, c, hi, c, layer, extend=False)
        return (hi, c, layer)

    def _json(self):
        return {"direction": self.direction,
                "at": self.at.toJson() if isinstance(self.at, Anchor) else None}

    @classmethod
    def _make(cls, o):
        return cls(Anchor.fromJson(o.get("at")), o.get("direction", "v"))

    def astuple(self):
        return (self.name, self.direction, repr(self.at))


@step
class _LayerTo(Step):
    """Change to a named layer. What `up`/`down` become once the search
    has already decided which layer it wants."""
    name = "layer"

    def __init__(self, layer):
        self.layer = layer

    def apply(self, path, cur):
        x, y, layer = cur
        if self.layer == layer:
            return cur
        path.drawVia(x, y, layer, self.layer)
        return (x, y, self.layer)

    def _json(self):
        return {"layer": self.layer}

    @classmethod
    def _make(cls, o):
        return cls(o.get("layer"))

    def astuple(self):
        return (self.name, self.layer)


def simplify(nodes):
    """A searched node list as its CORNERS.

    Drops every node that continues the run it is already on -- same
    layer, same direction -- so a forty-seven node staircase becomes
    the handful of turns it actually is.
    """
    pts = [(int(n[0]), int(n[1]), n[2]) for n in (nodes or [])]
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for prev, cur, nxt in zip(pts, pts[1:], pts[2:]):
        if cur[2] != prev[2] or cur[2] != nxt[2]:
            out.append(cur)          # a layer change is always a corner
            continue
        dx0, dy0 = cur[0] - prev[0], cur[1] - prev[1]
        dx1, dy1 = nxt[0] - cur[0], nxt[1] - cur[1]
        #- collinear iff the two steps point the same way on one axis
        if (dx0 == 0 and dx1 == 0) or (dy0 == 0 and dy1 == 0):
            continue
        out.append(cur)
    out.append(pts[-1])
    #- a layer change repeated at one point collapses to one corner
    dedup = [out[0]]
    for p in out[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    return dedup
