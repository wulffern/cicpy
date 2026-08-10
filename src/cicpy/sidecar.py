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

The recipe itself is inherited: SidecarCell subclasses SidecarPycell
(core/sidecarcell.py), so a cell that needs more than declarations
overrides beforePlace/afterPlace/beforeRoute/afterPaint and calls
super() -- the escape hatch is ordinary inheritance.

`compile()` turns the class into the spec dict the recipes consume;
detection in cic.py is by content: a module defining a SidecarCell
subclass is a sidecar, a module with module-level hooks and `data`
is a classic pycell, as ever.
"""
import itertools
import logging
import os
import sys

from cicpy.core.cellgroup import StackGroup
from cicpy.core.sidecarcell import SidecarPycell, HierLayoutCell

log = logging.getLogger("Sidecar")

_counter = itertools.count()

#- the declarative keys a subcell class may carry. Only keys the
#- class actually states reach the spec: presence matters downstream
#- (HierLayoutCell registers a channel only for a subcell that names
#- one).
_SUBCELL_KEYS = ("match", "group", "channel", "order", "fill")
_HOOK_NAMES = ("beforePlace", "beforeRoute")


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


def hooks_of(cls):
    """{hook name: plain function} the DESIGN declared on a subcell
    class. From the user classes' dicts, not getattr: the group base
    classes are framework and their methods are not hooks."""
    return _attrs(cls, _HOOK_NAMES)


class Subcell:
    """Marker mixin of a declared subcell: Stack/DiffPair/Mirror."""
    type = "stack"

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


class SidecarCell(SidecarPycell):
    """Base of a declared cell. Subclass, declare, done.

    Class declarations: `place` (flat-build knobs), nested Subcell
    classes, `rows` (the floorplan, bottom row first, referencing the
    classes), `supplies`, and for the assembled top `channel` (um
    between the rows) and `routes` (one ChannelRoute per crossing
    net). The recipe methods are inherited from SidecarPycell;
    override and call super() when the declarations cannot say it.
    """
    place = {}
    rows = []
    supplies = []
    channel = 8
    routes = None
    #- the LayoutCell class the hier build instantiates for the
    #- assembled top; a design subclasses HierLayoutCell and points
    #- here when the recipe's place()/route() cannot say it
    hier_cell = HierLayoutCell

    def __init__(self):
        super().__init__(type(self).compile())

    @classmethod
    def compile(cls):
        """The class as the spec dict the recipes consume."""
        cells = [v for base in _user_bases(cls)
                 for v in vars(base).values()
                 if isinstance(v, type) and issubclass(v, Subcell)]
        cells.sort(key=lambda c: c._sidecar_index)

        spec = {}
        if cls.place:
            spec["place"] = cls.place
        subcells = []
        for c in cells:
            entry = {"name": c.__name__, "type": c.type, "cls": c}
            entry.update(_attrs(c, _SUBCELL_KEYS))
            if "match" not in entry:
                log.warning(f"{cls.__name__}.{c.__name__}: no match "
                            f"regex; the subcell claims no instances")
            subcells.append(entry)
        spec["subcells"] = subcells
        if cls.rows:
            spec["rows"] = [[_name(n) for n in row] for row in cls.rows]
        if cls.supplies:
            spec["supplies"] = cls.supplies
        if cls.routes is not None:
            spec["hier"] = {"channel": cls.channel,
                            "routes": _normalize_routes(cls.routes),
                            "cell": cls.hier_cell}
        return spec


def _name(x):
    """A subcell reference as its name: the class itself, or a str."""
    return x if isinstance(x, str) else x.__name__


def _normalize_routes(routes):
    """The top's routes with class refs turned to names: drops accept
    the classes for the NameError guarantee, HierLayoutCell keys its
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


def sidecar_from_module(mod):
    """The module's SidecarCell, instantiated -- or None.

    None when the module defines no SidecarCell subclass of its own,
    which is what makes detection safe: a classic pycell that happens
    to import this module is still a classic pycell. When several are
    defined, the one named like the module wins.
    """
    cands = [v for v in vars(mod).values()
             if isinstance(v, type) and issubclass(v, SidecarCell)
             and v is not SidecarCell
             and getattr(v, "__module__", None) == mod.__name__]
    if not cands:
        return None
    for c in cands:
        if c.__name__ == mod.__name__:
            return c()
    if len(cands) > 1:
        log.warning(f"{mod.__name__}: {len(cands)} SidecarCell "
                    f"classes and none named like the module; "
                    f"taking {cands[0].__name__}")
    return cands[0]()


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
        log.error(f"{name}.py: import failed: {e}")
        return None
    return mod


def load_sidecar_spec(dirname, name):
    """The compiled spec of <dirname>/<name>.py, or None.

    None when there is no file, the import fails (loudly, in the
    log), or the module is a classic pycell rather than a sidecar.
    """
    mod = import_beside(dirname, name)
    if mod is None:
        return None
    for v in vars(mod).values():
        if (isinstance(v, type) and issubclass(v, SidecarCell)
                and v is not SidecarCell
                and getattr(v, "__module__", None) == mod.__name__):
            return v.compile()
    return None
