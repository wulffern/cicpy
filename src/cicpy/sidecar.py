"""The declarative sidecar: <CELL>.py IS the cell.

One class per cell, subclassing SidecarCell; one nested class per
subcell, subclassing the REAL placement groups (Stack is a
StackGroup), so a hook's `self` is the group that was actually built
-- group-scoped routing, live pins, the same object the recipe
placed. The floorplan, supplies and the assembled top are class
declarations on the cell itself, because the assembled top IS the
cell:

    from cicpy.sidecar import SidecarCell, Stack, Mirror

    class LELOTEMP_OTAR(SidecarCell):

        place = {"groupbreak": 6, "channel": 6}   # flat-build knobs

        class p_bias(Stack):
            match = r'^(xba\\d+|xstack_p_bias_(top|bot))$'
            group = "pmos"
            channel = "bias"                # named vertical channel
            order = ['xba1', 'xba8', 'xba2']

            def beforeRoute(self, entry):   # self IS the built group
                self.addConnectivityRoute(...)      # group-scoped
                self.layout.addConnectivityRoute(...)  # parent-scoped
                return None                 # True = fully routed here

        class n_mirr(Mirror):
            match = r'...'

        rows = [[n_load_a, n_load_b], [p_in_a, p_bias]]  # the classes
        supplies = [{"net": "VDD_1V8", "ring": "t", "strap": "top"}]

        channel = 8            # um between the rows in the top
        routes = [             # the top's ChannelRoutes; presence of
            {"net": "VCP", "track": 6,          # `routes` enables the
             "drops": [[n_mirr, "M2", "left"]]},  # hier build
        ]

The class name is the subcell name. `rows` and drop entries
reference the classes themselves, so a typo is a NameError at import
time, not an empty match at publish time.

Hooks are real methods -- (self, entry), where entry is the
subcell's plan (instances, ports, internal, type) -- and the
contract is checked by inheritance: the API they call is the group's
own, so a rename in cellgroup.py breaks the design file loudly.
beforePlace adjusts the stack before anything routes; beforeRoute
routes the subcell's internal nets and returns True to claim the
subcell as ROUTED (the built-in router leaves it alone), None to let
the built-in router take what it will. There is no class-level
`route` hook: LayoutCell.route() is a real method a class hook would
shadow. The file-based <SUBCELLNAME>.py escape hatch keeps the old
no-self contract, legacy `route` included.

The class IS the LayoutCell. SidecarCell subclasses both recipes in
core/sidecarcell.py -- SidecarPycell, which places devices, and
HierPycell, which builds a cell per subcell and assembles them -- so
a cell that needs more than declarations overrides beforePlace /
afterPlace / beforeRoute / place / route and calls super(); the
escape hatch is ordinary inheritance. There is ONE object per build:
the cell the framework builds is the instance of the design's own
class, and it is handed to itself as the pycell, so every hook the
design declares runs.

Which recipe a cell gets is a property of what it DECLARES, not of
how it was constructed: declare `routes` and the cell is made of
subcells -- hierarchy() splits its netlist, builds each part as a
cell and registers it, and place() tiles them -- otherwise it is made
of devices. One pass, one process, one object; there is no <CELL>_HIER
scaffold, no generated netlist between two passes, and no role to
pass to a constructor.

`compile()` turns the class into the spec dict the recipes consume;
detection in cic.py is by content: a module defining a SidecarCell
subclass is a sidecar, a module with module-level hooks and `data`
is a classic pycell, as ever.
"""
import itertools
import logging
import re
import os
import sys

from cicpy.core.cellgroup import StackGroup
from cicpy.core.layoutcell import LayoutCell
from cicpy.core.sidecarcell import SidecarPycell, HierPycell

log = logging.getLogger("Sidecar")

_counter = itertools.count()

#- the declarative keys a subcell class may carry. Only keys the
#- class actually states reach the spec: presence matters downstream
#- (the assembly registers a channel only for a subcell that names
#- one).
_SUBCELL_KEYS = ("match", "group", "channel", "order", "fill", "xspace",
                 "wires", "wires_key")
def _user_bases(cls):
    """The design-authored classes of cls's MRO, base first.

    Everything defined under cicpy is framework; everything else is
    the design's, including an intermediate base a design writes for
    shared defaults.
    """
    return [b for b in reversed(cls.__mro__)
            if not (b.__module__ or "").startswith("cicpy.")
            and b is not object]


def _attrs(cls, keys):
    out = {}
    for base in _user_bases(cls):
        for k in keys:
            if k in vars(base):
                out[k] = vars(base)[k]
    return out


class Subcell:
    """Marker mixin of a declared subcell: Stack/DiffPair/Mirror.

    AND THE PHASES, as the no-ops a design overrides. These are the
    same eight LayoutCell.layout() dispatches, so a subcell class and
    a cell class are written the same way -- override the phase you
    care about, call super() if the base does anything.

    They are methods, not a registry: there was a `_HOOK_NAMES`
    whitelist and a `hooks_of()` that read the design's class dicts to
    tell a declared hook from an inherited one, and neither buys
    anything. Every one of these names is free on StackGroup, so
    calling the method IS the dispatch, and a design that declares
    none pays for nothing. (`route` is the one name that cannot join
    them: Cell.route is real, and a hook would shadow it.)

    `beforeRoute` is the only one whose return value is read: True
    means "this subcell is routed, the built-in router must not touch
    it".
    """
    type = "stack"

    def beforePlace(self, entry):
        return None

    def afterPlace(self, entry):
        return None

    def beforeRoute(self, entry):
        return None

    def afterRoute(self, entry):
        return None

    def beforePaint(self, entry):
        return None

    def afterPaint(self, entry):
        return None

    def beforePorts(self, entry):
        return None

    def afterPorts(self, entry):
        return None

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        #- declaration order is spec order: membership regexes are
        #- tried first to last, so the file reads specific to general
        cls._sidecar_index = next(_counter)


class Stack(Subcell, StackGroup):
    """A declared subcell that IS the StackGroup the recipe builds."""
    type = "stack"

    def __init__(self, layout, name=None):
        StackGroup.__init__(self, layout, name or type(self).__name__)
        self.kind = self.type


class DiffPair(Stack):
    type = "diffpair"

    def routeInternal(self):
        return (f"no {self.kind} router yet; ship a beforeRoute hook "
                f"on {type(self).__name__} or retype it")


class Mirror(Stack):
    type = "mirror"

    def routeInternal(self):
        return (f"no {self.kind} router yet; ship a beforeRoute hook "
                f"on {type(self).__name__} or retype it")


class SidecarCell(SidecarPycell, HierPycell, LayoutCell):
    """Base of a declared cell -- and the cell. Subclass, declare, done.

    Class declarations: `place` (placement knobs), nested Subcell
    classes, `rows` (the floorplan, bottom row first, referencing the
    classes), `supplies`, and for a cell made of subcells `channel`
    (um between the rows) and `routes` (one ChannelRoute per crossing
    net).

    WHAT A CELL IS MADE OF is what `routes` decides. Declared, the
    cell is made of SUBCELLS: hierarchy() splits its netlist, builds
    each part as a cell of its own and registers it, place() tiles
    them and route() lays the crossing nets. Undeclared, the cell is
    made of DEVICES: the flat recipe places, fills, taps and routes
    them. Either way it is one object, one pass, one process.

    An instance IS the LayoutCell the framework builds, and its own
    pycell -- so beforePlace, afterPlace, beforeRoute, afterPorts and
    the rest are the cell's own methods. The hook-shaped half of the
    flat recipe belongs to a cell made of devices; a design's own
    overrides belong to the cell whatever it is made of.
    """
    rows = []
    supplies = []
    channel = 8
    routes = None
    #- `place` the declaration and place() the method are the same
    #- name on the same object now, so the declaration is read off
    #- the class ONCE, here, and taken off it -- see _place
    _place = {}

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        knobs = vars(cls).get("place")
        if isinstance(knobs, dict):
            cls._place = knobs
            delattr(cls, "place")

    def __init__(self, spec=None):
        LayoutCell.__init__(self)
        #- from the CLASS, which is the usual way, or from a spec --
        #- which is how a piece of a parent is built. Same object,
        #- same recipe; only where the declaration came from differs.
        self.spec = type(self).compile() if spec is None else spec
        self.noPowerRoute = True
        #- the flat recipe's data-driven half. resetOrigins is about
        #- placed devices; a cell that has none simply has nothing to
        #- reset, so this is not a switch either.
        self.data = SidecarPycell.recipe_data()

    #- WHAT A CELL IS MADE OF IS NOT A FLAG. It used to be
    #- `made_of_subcells`, read off whether `routes` was declared, and
    #- every step of the interface was guarded by it -- so overriding
    #- beforeRoute and calling super() ran the flat recipe or nothing
    #- at all depending on a declaration elsewhere in the class. What
    #- decides is CONTENT: a cell holds child cells, or it holds
    #- stacks of devices, and the two are mutually exclusive because
    #- a declared piece is always built as a cell.

    @property
    def subcells(self):
        """The pieces this cell is assembled from."""
        return self.spec.get("subcells", []) or []

    @property
    def stacks(self):
        """The device columns this cell places itself."""
        return self.spec.get("stacks", []) or []

    # -- the cell's own methods; what it HOLDS picks the recipe

    def place(self):
        if self.subcells:
            HierPycell.placeHier(self)
        else:
            LayoutCell.place(self)

    def route(self):
        if self.subcells:
            HierPycell.routeHier(self)
        else:
            LayoutCell.route(self)

    #- and no wrappers for beforePlace / afterPlace / beforeRoute:
    #- they are inherited. They existed to hold the `if not
    #- made_of_subcells` guards, and forwarding to the class you
    #- already inherit from is the same method twice -- with the
    #- added cost that a design's super() call resolved here rather
    #- than at the recipe.

    @classmethod
    def compile(cls):
        """The class as the spec dict the recipes consume."""
        cells = [v for base in _user_bases(cls)
                 for v in vars(base).values()
                 if isinstance(v, type) and issubclass(v, Subcell)]
        cells.sort(key=lambda c: c._sidecar_index)

        spec = {}
        if cls._place:
            spec["place"] = cls._place
        subcells = []
        for c in cells:
            entry = {"name": c.__name__, "type": c.type, "cls": c}
            entry.update(_attrs(c, _SUBCELL_KEYS))
            #- A DECLARATION THAT CANNOT CLAIM ANYTHING IS DROPPED, not
            #- warned about and kept. `plan_from_netlist` reads
            #- `s["match"]` and compiles it, so a subcell with none is
            #- a KeyError and one with a broken regex is an re.error --
            #- the whole build dies for a typo in one class, and the
            #- message names neither the cell nor the subcell.
            if not entry.get("match"):
                log.warning(f"{cls.__name__}.{c.__name__}: no match "
                            f"regex; the subcell claims no instances "
                            f"and is dropped")
                continue
            try:
                re.compile(str(entry["match"]))
            except re.error as e:
                log.error(f"{cls.__name__}.{c.__name__}: bad match "
                          f"regex {entry['match']!r}: {e}; dropped")
                continue
            _warn_absolute_wires(f"{cls.__name__}.{c.__name__}", entry)
            subcells.append(entry)
        spec["subcells"] = subcells
        if cls.rows:
            spec["rows"] = [[_name(n) for n in row] for row in cls.rows]
        if cls.supplies:
            spec["supplies"] = cls.supplies
        if cls.routes is not None:
            spec["hier"] = {"channel": cls.channel,
                            "routes": _normalize_routes(cls.routes)}
        return spec


def _name(x):
    """A subcell reference as its name: the class itself, or a str."""
    return x if isinstance(x, str) else x.__name__


def _normalize_routes(routes):
    """The top's routes with class refs turned to names: drops accept
    the classes for the NameError guarantee, the assembly keys its
    overrides by instance name."""
    out = []
    for r in routes:
        r = dict(r)
        drops = []
        for d in r.get("drops") or []:
            if isinstance(d, dict):
                d = dict(d)
                d["inst"] = _name(d["inst"])
            else:
                d = [_name(d[0])] + list(d[1:])
            drops.append(d)
        if "drops" in r:
            r["drops"] = drops
        out.append(r)
    return out


def _warn_absolute_wires(where, entry):
    """A `wires` block holding a COORDINATE, said where it is written.

    An anchor -- trunktab, trunkright, trunkleft -- is recomputed from
    the net's own pins every run, so it survives a resize and another
    technology and it says why the wire is there. A trunkx does none of
    that, and it cannot even be checked: the fingerprint that guards a
    wires block is translation-invariant by design, so a coordinate
    resolved against another placement replays silently. That happened
    to three blocks in one design and was found only by measuring the
    geometry.

    The router writes anchors now (mazerouter.anchored_options), so a
    coordinate here is either hand-typed or generated before that --
    both worth saying out loud. Not an error: a trunk that genuinely
    lies on no pin anchor has nothing else to be yet.
    """
    for w in (entry.get("wires") or []):
        if len(w) < 4:
            continue
        m = re.search(r"(trunkx|bandy)=?(-?\d+)", str(w[3]))
        if m:
            log.warning(
                f"{where}: {w[0]} is wired to the coordinate "
                f"{m.group(0)}. A coordinate survives neither a resize "
                f"nor another technology, and a stale one replays "
                f"without complaint -- prefer trunktab / trunkright / "
                f"trunkleft, which the router now emits.")


def sidecar_from_module(mod):
    """The module's SidecarCell class -- or None.

    The CLASS, not an instance: the caller registers it with the
    Design and the framework instantiates it as the cell being built
    (see cic.py). None when the module defines no SidecarCell
    subclass of its own, which is what makes detection safe: a
    classic pycell that happens to import this module is still a
    classic pycell. When several are defined, the one named like the
    module wins.
    """
    cands = [v for v in vars(mod).values()
             if isinstance(v, type) and issubclass(v, SidecarCell)
             and v is not SidecarCell
             and getattr(v, "__module__", None) == mod.__name__]
    if not cands:
        return None
    for c in cands:
        if c.__name__ == mod.__name__:
            return c
    if len(cands) > 1:
        log.warning(f"{mod.__name__}: {len(cands)} SidecarCell "
                    f"classes and none named like the module; "
                    f"taking {cands[0].__name__}")
    return cands[0]


def import_beside(dirname, name, reload=False):
    """Import <dirname>/<name>.py the pycell way, or None.

    THE one lookup -- dirname + name + ".py", dirname on sys.path,
    import through sys.modules -- shared by the sidecar loader, the
    per-stack pycell runner and cic.py's own pycell import, which
    each used to carry their own copy with drifted guards. `reload`
    re-executes the module (the per-stack runner wants edits picked
    up between runs); everything else reuses what is loaded.
    """
    import importlib
    dirname = dirname or ""
    if not os.path.exists(os.path.join(dirname, name + ".py")):
        return None
    if dirname and dirname not in sys.path:
        sys.path.append(dirname)
    try:
        mod = importlib.import_module(name)
        if reload:
            mod = importlib.reload(mod)
    except Exception as e:
        #- A FILE THAT EXISTS AND WILL NOT IMPORT IS A HARD ERROR.
        #- Returning None means "there is no pycell here", and the
        #- build then goes on to place the cell some other way -- for
        #- a sidecar, that is the flat fallback, which quietly
        #- OVERWRITES a good layout with a wrong one. Measured: a
        #- stray indent in LELO_TEMP.py, and the top came out as
        #- eleven devices in a column with every block dissolved.
        #- A file that is not there is still None; one that is there
        #- and broken stops the run.
        log.error(f"{name}.py: import failed: {e}")
        raise
    return mod


def load_sidecar_class(dirname, name):
    """The SidecarCell class declared by <dirname>/<name>.py, or None.

    None when there is no file, the import fails (loudly, in the
    log), or the module is a classic pycell rather than a sidecar.
    """
    mod = import_beside(dirname, name)
    if mod is None:
        return None
    return sidecar_from_module(mod)


def load_sidecar_spec(dirname, name):
    """The compiled spec of <dirname>/<name>.py, or None."""
    cls = load_sidecar_class(dirname, name)
    return None if cls is None else cls.compile()
