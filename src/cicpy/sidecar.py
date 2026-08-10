"""The declarative python sidecar: <CELL>.py IS the cell.

The sidecar used to be YAML. The same declarations are now python
classes, for the reasons a hand-edited file wants to be python: real
syntax errors at import instead of silent no-matches, regexes without
quoting rules, and the imperative escape hatch -- a hook that routes
what the recipe cannot say -- living as a method beside the
declaration it belongs to instead of in a ninth file.

A sidecar module looks like this:

    from cicpy.sidecar import Stack, Mirror, Hier

    place = {"groupbreak": 6, "channel": 6}

    class p_bias(Stack):
        match = r'^(xba\\d+|xstack_p_bias_(top|bot))$'
        group = "pmos"
        channel = "bias"
        order = ['xba1', 'xba8', 'xba2']

        def beforeRoute(layout, entry):      # no self: hooks are
            ...                              # plain functions
            return None

    rows = [[n_load_a, n_load_b], [p_in_a, p_bias]]   # the classes
    supplies = [{"net": "VDD_1V8", "ring": "t", "strap": "top"}]

    class hier(Hier):
        channel = 8
        routes = [{"net": "VCP", "track": 6,
                   "drops": [["n_mirr", "M2", "left"]]}]

The class name is the subcell name. `rows` references the classes
themselves, so a typo is a NameError at import time, not an empty
match at publish time. Hooks are written WITHOUT self -- they are
collected from the class dict as plain functions and called exactly
like a per-subcell pycell's: beforePlace(layout, entry),
beforeRoute(layout, entry) returning True to claim the subcell as
routed, or the legacy route(layout, entry) whose existence alone
claims it.

spec_from_module compiles the module into the same spec dict the YAML
used to load into, so `SidecarPycell` and `AssemblyPycell`
(core/sidecarcell.py) execute it unchanged. Detection is by content:
a module defining Subcell subclasses is a sidecar; a module defining
`data` or module-level hooks is a classic pycell, as ever.
"""
import itertools
import logging
import os
import sys

log = logging.getLogger("Sidecar")

_counter = itertools.count()

#- the declarative keys a subcell class may carry, in spec order.
#- Only keys the class actually states reach the spec: presence
#- matters downstream (AssemblyPycell registers a channel only for a
#- subcell that names one).
_SUBCELL_KEYS = ("match", "group", "channel", "order", "fill")
_HOOK_NAMES = ("beforePlace", "beforeRoute", "route")
_HIER_KEYS = ("channel", "routes")


class Subcell:
    """Base of a declared subcell. Subclass Stack/DiffPair/Mirror."""
    type = "stack"

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        #- declaration order is spec order: membership regexes are
        #- tried first to last, so the file reads specific to general
        cls._sidecar_index = next(_counter)


class Stack(Subcell):
    type = "stack"


class DiffPair(Subcell):
    type = "diffpair"


class Mirror(Subcell):
    type = "mirror"


class Hier:
    """Base of the `hier` class: the assembled top's declarations."""


_FRAMEWORK = (Subcell, Stack, DiffPair, Mirror, Hier)


def _attrs(cls, keys):
    """The declared attributes of cls, walking user bases only.

    vars() over the reversed MRO, stopping at the framework classes,
    so an intermediate base a design writes for shared defaults works
    the obvious way.
    """
    out = {}
    for base in reversed(cls.__mro__):
        if base is object or base in _FRAMEWORK:
            continue
        for k in keys:
            if k in vars(base):
                out[k] = vars(base)[k]
    return out


def hooks_of(cls):
    """{hook name: plain function} declared on a subcell class.

    From the class DICT, not getattr: hooks are written without self,
    and the raw function is what a pycell hook already is.
    """
    return _attrs(cls, _HOOK_NAMES)


def spec_from_module(mod):
    """Compile a sidecar module into the spec dict, or None.

    None when the module declares no Subcell subclass of its own --
    which is what makes detection safe: a classic pycell that happens
    to import this module is still a classic pycell.
    """
    cells = [v for v in vars(mod).values()
             if isinstance(v, type) and issubclass(v, Subcell)
             and v not in _FRAMEWORK
             and getattr(v, "__module__", None) == mod.__name__]
    if not cells:
        return None
    cells.sort(key=lambda c: c._sidecar_index)

    spec = {}
    place = getattr(mod, "place", None)
    if isinstance(place, dict):
        spec["place"] = place

    subcells = []
    for cls in cells:
        entry = {"name": cls.__name__, "type": cls.type}
        entry.update(_attrs(cls, _SUBCELL_KEYS))
        if "match" not in entry:
            log.warning(f"{mod.__name__}.{cls.__name__}: no match "
                        f"regex; the subcell claims no instances")
        subcells.append(entry)
    spec["subcells"] = subcells
    spec["classes"] = {cls.__name__: cls for cls in cells}

    rows = getattr(mod, "rows", None)
    if rows:
        spec["rows"] = [[n if isinstance(n, str) else n.__name__
                         for n in row] for row in rows]
    supplies = getattr(mod, "supplies", None)
    if supplies:
        spec["supplies"] = supplies

    hier = getattr(mod, "hier", None)
    if isinstance(hier, dict):
        spec["hier"] = _normalize_hier(hier)
    elif isinstance(hier, type) and issubclass(hier, Hier):
        spec["hier"] = _normalize_hier(_attrs(hier, _HIER_KEYS))
    return spec


def _name(x):
    """A subcell reference as its name: the class itself, or a str."""
    return x if isinstance(x, str) else x.__name__


def _normalize_hier(h):
    """A copy of the hier declaration with class refs turned to names.

    `rows` takes the classes so a typo is a NameError; the drops in
    `hier.routes` deserve the same, but AssemblyPycell keys its
    overrides by instance NAME, so the classes are resolved here.
    """
    h = dict(h)
    routes = []
    for r in h.get("routes") or []:
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
        routes.append(r)
    if "routes" in h:
        h["routes"] = routes
    return h


def load_sidecar_spec(dirname, name):
    """The spec of <dirname>/<name>.py, or None.

    None when there is no file, the import fails (loudly, in the
    log), or the module is a classic pycell rather than a sidecar.
    Import goes through sys.modules like every pycell import does, so
    the module cic.py already loaded is reused, not re-executed.
    """
    import importlib
    dirname = dirname or ""
    if not os.path.exists(os.path.join(dirname, name + ".py")):
        return None
    if dirname and dirname not in sys.path:
        sys.path.append(dirname)
    try:
        mod = importlib.import_module(name)
    except Exception as e:
        log.error(f"{name}.py: sidecar import failed: {e}")
        return None
    return spec_from_module(mod)
