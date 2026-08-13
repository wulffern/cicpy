#- --------------------------------------------------------------------
#- Subcell publication
#- --------------------------------------------------------------------
#- What a cell's subcells ARE, read off a placed layout: the plan
#- that names them (plan_subcells / subcell_spec / subcell_membership
#- / subcell_groups), the netlist each one publishes (stack_subckt),
#- and their per-subcell hooks (run_stack_pycells). BUILDING them as
#- cells is core/hierarchy.py and core/sidecarcell.py, from the
#- netlist and before any placement.
#- Routing itself lives in mazerouter.py; this module only imports
#- from it.

import logging
import re

from .rect import Rect
from .rules import Rules
from .mazerouter import (MazeRouter, stack_of, pins_by_stack,
                         supply_nets, route_stack_level)


def subcell_spec(layout):
    """The design's subcell declarations, from its sidecar module.

    ``<CELL>.py`` beside the design -- the cell's one declarative
    sidecar (see cicpy/sidecar.py): a Subcell subclass per subcell,
    its name the class name, its membership the `match` regex, its
    kind the base class (Stack | DiffPair | Mirror).

    Declarative on purpose. A subcell is a statement about the DESIGN
    -- which devices form a unit, and what kind of unit -- and a
    statement belongs in a declaration that can be read without
    running anything, rather than in whichever pycell hook happens to
    build the groups. The type is the router's hint: a diffpair wants
    its halves routed symmetrically, a mirror wants gates bussed, a
    stack wants the series links. Only the stack router exists today,
    and the others say so instead of routing wrongly.

    The spec is read off the layout when SidecarPycell already loaded
    it (one truth, compiled once), and from the module on disk
    otherwise. Returns [{name, match (compiled), type}], or [].
    """
    log = logging.getLogger("MazeRouter")
    spec = getattr(layout, "_sidecar_spec", None)
    if spec is None:
        from cicpy.sidecar import load_sidecar_spec
        dirname = getattr(layout, "dirname", "") or ""
        spec = load_sidecar_spec(dirname, layout.name)
    if not spec:
        return []
    out = []
    for entry in spec.get("subcells") or []:
        name = str(entry.get("name", "") or "")
        match = str(entry.get("match", "") or "")
        if not name or not match:
            log.warning(f"{layout.name} sidecar: a subcell needs both "
                        f"name and match: {entry}")
            continue
        try:
            rx = re.compile(match)
        except re.error as e:
            log.error(f"{layout.name} sidecar: {name}: bad match "
                      f"regex: {e}")
            continue
        out.append({"name": name, "match": rx,
                    "type": str(entry.get("type", "stack") or "stack")})
    return out


def subcell_membership(layout):
    """{instance name: subcell name}, from the sidecar, else the groups.

    A SUBCELL is whatever the design wants to publish as a cell of its
    own. Three ways to be one, checked in this order:

      1. an entry in the ``<CELL>.py`` sidecar whose ``match`` regex
         takes the instance name. First entry wins, so order the file
         from specific to general. See subcell_spec.
      2. any CellGroup with ``subcell = True`` set on it.
      3. failing both, a StackGroup. A column of devices is the
         decomposition that needs no thought, so it is the default.

    A stack is identified by TYPE, not by shape: a StackGroup's children
    include RouteBundles, which carry `.instances` too, so "a group with
    instances and no sub-groups" walks past the real stack onto a bundle
    -- and bundles have no tap_instances, so every tap then falls into a
    pseudo-subcell of its own.

    Falls back to the leading non-digit run of the instance name, which
    is ciccreator's placement-group rule, when a design has no groups --
    a .cic reloaded from disk has none.

    ONE definition, shared with pins_by_stack and the router. They used
    to disagree -- this walked the CellGroups, that used the instance
    name prefix -- and asking the router for a subcell by name then
    matched nothing and reported 0 routed, 0 blocked, which reads
    exactly like success.
    """
    from cicpy.core.cellgroup import CellGroup, StackGroup
    member = {}

    spec = subcell_spec(layout)
    if spec:
        #- A DESIGN WITH A SIDECAR IS DECLARED, FULL STOP. The declared
        #- entries are the subcells; the group walk does not add more
        #- behind the file's back. What the regexes fail to claim is
        #- reported by plan_subcells, with the instance names the
        #- missing entry would be written from.
        for inst in layout.iterInstances():
            nm = getattr(inst, "instanceName", "") or ""
            if not nm or nm in member:
                continue
            for entry in spec:
                if entry["match"].search(nm):
                    member[nm] = entry["name"]
                    break
        return member

    def _claim(grp, gname):
        for inst in (list(getattr(grp, "instances", []) or [])
                     + list(getattr(grp, "tap_instances", []) or [])):
            nm = getattr(inst, "instanceName", "") or ""
            if nm and gname and nm not in member:
                member[nm] = gname
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                _claim(c, gname)

    #- the groups fill in around the sidecar, never over it: _claim
    #- respects an instance the sidecar already took
    for gname, grp in iter_subcell_groups(layout):
        _claim(grp, gname)
    return member


#- the old name, kept because it reads correctly wherever the subcell
#- IS a stack, which is still the common case
stack_membership = subcell_membership


def iter_subcell_groups(layout):
    """Yield (name, group) for every group that IS a subcell: one the
    design marked with ``subcell = True``, else any StackGroup -- a
    column of devices is the decomposition that needs no thought.
    Below a claimed group is routing, not placement, so the walk does
    not descend into it.

    THE one walk. subcell_membership and subcell_groups both consume
    it; they used to carry their own copies of it, with a comment
    begging to keep them in step.
    """
    from cicpy.core.cellgroup import CellGroup, StackGroup

    def _walk(grp):
        if getattr(grp, "subcell", False) or isinstance(grp, StackGroup):
            nm = getattr(grp, "name", "")
            if nm:
                yield nm, grp
            return
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                yield from _walk(c)

    for grp in getattr(layout, "cellgroups", []) or []:
        yield from _walk(grp)


def subcell_groups(layout):
    """{subcell name: the CellGroup itself}.

    The group, not just its instance names, because
    CellGroup.addConnectivityRoute scopes itself -- it builds its own
    instanceRegex and takes a different path through getNodeAccessRects
    than passing includeInstances by hand does. The hand written routes
    that worked all went through the group.
    """
    return dict(iter_subcell_groups(layout))


stack_groups = subcell_groups


def run_stack_pycells(layout, log=None, parent_name=None):
    """Let each stack that ships a `<STACKCELL>.py` route itself.

    Called by LayoutCell.layout() between afterPlace and beforeRoute, so
    the Routes a stack pycell creates are drawn by the same route() pass
    as everything else. Returns the set of stack keys that were handled.

    Opt-in by the file existing. A design with no stack pycells -- which
    is every design but one today -- sees no change at all.

    The stacks handled here are remembered on the layout so
    route_stack_level will not route them a second time: a stack that
    has said how it wants to be wired has said it.
    """
    log = log or logging.getLogger("MazeRouter")
    handled = set()
    try:
        plan = plan_subcells(layout, parent_name)
    except Exception as e:
        log.warning(f"could not plan stack cells: {e}")
        return handled
    for entry in plan:
        if _run_stack_pycell(layout, entry, log):
            handled.add(entry["stack"])
    if handled:
        log.info(f"stack pycells routed: {sorted(handled)}")
    layout._stacks_routed_by_pycell = handled
    return handled


def plan_subcells(layout, parent_name=None):
    """What subcells the stacks would become, without making any.

    Returns [{name, stack, instances, ports, internal}] where `ports`
    are the nets that cross the stack boundary -- the ones the parent
    still has to route -- and `internal` are the nets wholly inside it,
    which the stack owns and nobody above needs to see.

    Deliberately analysis only. Turning a group into a real subcell
    means three separate things, and knowing the shape first is what
    makes them separable:

      1. a LayoutCell registered in design.cells, or no .mag is written
         for it. Nesting alone does NOT do this: DesignPrinter flattens
         a nested LayoutCell into its parent
         (designprinter.py: `elif child.isLayoutCell(): printChildren`).
      2. an Instance of it in the parent, so the parent references
         rather than contains.
      3. a subckt for the schematic side, synthesised from the devices
         in the stack with the boundary nets as its ports -- LVS needs
         something to compare the extracted stack against, and the
         xschem source has no such hierarchy.

    The port list is the whole payoff. Everything in `internal` stops
    existing as far as the parent is concerned.
    """
    from collections import defaultdict
    counts = defaultdict(lambda: defaultdict(int))
    insts = defaultdict(list)
    #- The CellGroups the design actually built, when it built any.
    #- The name-prefix rule is a fallback and it is WRONG for taps and
    #- fillers: addTaps names them after the GROUP (xstack_n_load_a_bot)
    #- while the devices are named by prefix (xnd, xns), so a prefix
    #- grouping puts every tap in a one-instance stack of its own --
    #- measured, 17 bogus stacks out of 25.
    #- One definition of "which stack is this instance in", shared with
    #- pins_by_stack. They used to disagree -- this walked the
    #- CellGroups and gave the stack's name, that used the instance
    #- name prefix -- so asking the router for a stack by name matched
    #- nothing and
    #- reported 0 routed, 0 blocked, which reads exactly like success.
    member = subcell_membership(layout)

    for inst in layout.iterInstances():
        name = getattr(inst, "instanceName", "") or ""
        st = member.get(name) or stack_of(name)
        if not st:
            continue
        insts[st].append(name)
        member[name] = st
    for net in getattr(layout, "nodeGraphList", []):
        g = layout.nodeGraph.get(net)
        if g is None:
            continue
        for port in getattr(g, "ports", []):
            inst = getattr(port, "parent", None)
            nm = getattr(inst, "instanceName", "") if inst else ""
            if nm:
                counts[member.get(nm) or stack_of(nm)][net] += 1
    #- how many stacks does each net appear in?
    spread = defaultdict(int)
    for st in counts:
        for net in counts[st]:
            spread[net] += 1

    #- A NET THAT IS A PORT OF THE PARENT IS A PORT OF THE STACK, even
    #- when every device pin on it happens to sit in one stack.
    #-
    #- "Appears in more than one stack" is the right test for an
    #- internal node and the wrong one for a boundary. Measured: an
    #- input pair's gate net had all six of its pins inside one stack,
    #- so it was classed internal and the generated cell did not expose
    #- it -- a stack that swallows the parent's input, with no way to
    #- drive it once the parent instantiates the cell rather than
    #- containing it.
    parent_ports = set()
    for attr in ("allPortNames", "ports"):
        try:
            parent_ports.update(getattr(layout, attr, None) or ())
        except TypeError:
            pass
    ckt = getattr(layout, "ckt", None)
    for nm in (getattr(ckt, "nodes", None) or ()):
        parent_ports.add(nm)

    #- the declared type rides along; "stack" when undeclared, because
    #- that is what an undeclared subcell IS -- one the StackGroup walk
    #- found
    spec = subcell_spec(layout)
    types = {e["name"]: e["type"] for e in spec}
    #- A DESIGN THAT DECLARES, DECLARES EVERYTHING. Once a sidecar
    #- exists the decomposition is a stated decision, and a subcell that
    #- appears anyway -- found by the group walk, not the file -- is the
    #- statement being incomplete. Say so, with the entry that would
    #- close the gap. Not an error: the fallback is what lets a design
    #- adopt the file one subcell at a time.
    if spec:
        claimed_insts = {nm for nm, st in member.items()}
        loose = sorted(nm for inst in layout.iterInstances()
                       for nm in [getattr(inst, "instanceName", "") or ""]
                       if nm and nm not in claimed_insts)
        if loose:
            log = logging.getLogger("MazeRouter")
            log.warning(
                f"{layout.name} sidecar claims no subcell for "
                f"{len(loose)} instances: {', '.join(loose[:8])}"
                + (" ..." if len(loose) > 8 else ""))
    out = []
    for st in sorted(insts):
        nets = counts.get(st, {})
        ports = sorted(n for n in nets
                       if spread[n] > 1 or n in parent_ports)
        internal = sorted(n for n in nets
                          if spread[n] == 1 and n not in parent_ports)
        out.append({
            "name": f"{parent_name or layout.name}_{st}".upper(),
            "stack": st,
            "type": types.get(st, "stack"),
            "instances": sorted(insts[st]),
            "ports": ports,
            "internal": internal,
        })
    return out


plan_stack_cells = plan_subcells


def stack_subckt(layout, entry):
    """Synthesise the schematic side of a stack subcell.

    Returns (lines, fingerprint). The lines are a spice subckt built
    from the devices actually in the stack, with the boundary nets as
    its ports; the fingerprint is what those devices and their
    connections are, so a silent change can be detected.

    GENERATED, never edited. That is the answer to the obvious worry
    about a hand-maintained substack schematic drifting from the layout:
    there is nothing to drift, because both sides come from the same
    netlist and grouping and are rebuilt together every run.

    The fingerprint guards the one thing regeneration cannot: the
    GROUPING changing without anyone noticing. Instance names decide
    placement groups (ciccreator subcktinstance.cpp:24), so a rename
    silently moves a device to another stack -- and both the schematic
    and the layout would then agree, wrongly and consistently.
    """
    import hashlib
    devices = []
    fills = []
    for inst in layout.iterInstances():
        name = getattr(inst, "instanceName", "") or ""
        if name not in entry["instances"]:
            continue
        nodes = list(getattr(inst, "instancePortsList", []) or [])
        #- the SCHEMATIC cell, not the layout one. They differ for a
        #- diode connected device, which is placed as the D variant.
        cell = (getattr(inst, "schematicCell", "")
                or getattr(inst, "cell", "") or "")
        #- An instance with no nodes is layout, not circuit -- but the
        #- two kinds of layout differ in what magic makes of them, and
        #- LVS only forgives one:
        #-
        #-   taps    guard and well, no transistor. Extract as geometry
        #-           and appear in no netlist. Skip.
        #-   FILLS   a real transistor. Magic extracts it -- measured,
        #-           D, G and S each floating on its own node and B on
        #-           the stack's supply -- and a schematic without it is
        #-           one device short, every time, on every subcell.
        #-
        #- So a fill is emitted the way it extracts: the layout straps
        #- D/G/S and ties the strap into the tap row, so every terminal
        #- rides the stack's supply.
        if not nodes:
            if name.startswith("xfill_"):
                fills.append((name, cell))
            continue
        devices.append((name, nodes, cell))
    devices.sort()

    #- which pin is bulk, and which net it rides: read it off the
    #- SIBLINGS. Every real device in the stack ties one terminal to a
    #- supply; the position of that terminal in the cell's port order is
    #- the bulk index, and the net is the stack's supply. Asking the
    #- devices beats naming "B": a library is free to call it anything.
    supplies = supply_nets(layout)

    def _bulk_of(dev_list):
        #- The bulk index is the one on a supply in EVERY sibling; a
        #- source can ride the supply too (a whole bias stack does),
        #- but not on all devices of all stacks -- and when both
        #- qualify, bulk is the later terminal. Taking the FIRST
        #- supply position put the fill's supply on S in p_bias,
        #- where magic extracts B on the well and S floating.
        if not dev_list:
            return None, None
        width = min(len(d[1]) for d in dev_list)
        for i in reversed(range(width)):
            nets = {d[1][i] for d in dev_list}
            if nets and all(nd in supplies for nd in nets):
                return i, dev_list[0][1][i]
        for i in reversed(range(width)):
            nd = dev_list[0][1][i]
            if nd in supplies:
                return i, nd
        return None, None

    for name, cell in sorted(fills):
        sibs = [d for d in devices
                if d[2] == cell or d[2].startswith(cell)]
        bulk_i, bulk_net = _bulk_of(sibs)
        if bulk_i is None:
            #- no sibling of the same cell: fall back to any device
            bulk_i, bulk_net = _bulk_of(devices)
        if bulk_i is None:
            continue
        width = max((len(d[1]) for d in devices), default=4)
        #- every terminal on the stack's supply: the layout straps the
        #- dummy and ties the strap into the tap row, so the extractor
        #- sees D=G=S=B on the supply and the netlist says the same.
        nodes = [bulk_net] * width
        devices.append((name, nodes, cell))
    devices.sort()
    ports = list(entry["ports"])
    lines = [f".subckt {entry['name']} {' '.join(ports)}"]
    for name, nodes, cell in devices:
        lines.append(f"{name} {' '.join(nodes)} {cell}")
    lines.append(".ends")
    key = "|".join(f"{n}:{c}:{','.join(nd)}" for n, nd, c in devices)
    key += "||" + ",".join(sorted(ports))
    return lines, hashlib.sha1(key.encode()).hexdigest()[:12]


def design_of(layout):
    """The Design a layout belongs to.

    `layout.design` is None during a pycell hook -- it is set later --
    so a hook that asks for it silently does nothing. `layout.parent` is
    the MagicDesign and is set, which is the same route cellgroup.py
    already takes to reach getLayoutCell.
    """
    for attr in ("design", "parent"):
        d = getattr(layout, attr, None)
        if d is not None and hasattr(d, "cells") and hasattr(d, "cellnames"):
            return d
    return None


def _run_stack_pycell(layout, entry, log, cell=None):
    """Run this subcell's own hooks, from the sidecar class or a file.

    Two places a subcell's hooks can live, tried in this order:

      1. methods on the subcell's own class in the <CELL>.py sidecar
         -- beforePlace(self, entry) / beforeRoute(self, entry),
         where self IS the built group (a Stack is a StackGroup), so
         group-scoped routing is self.addConnectivityRoute and the
         parent is self.layout. See cicpy/sidecar.py.
      2. its own <STACKCELL>.py beside the design -- same lookup as
         cic.py's, dirname + name + ".py" on sys.path. The escape
         hatch keeps the old module contract: plain functions
         (layout, entry), legacy route() included.

    The hook is `route(layout, entry)`: the parent the stack came from,
    and its plan entry. The parent is passed because the node graph
    belongs to it -- a stack holds the instances but not the netlist, so
    its pins are only findable through the parent until the flow builds
    each stack from its own generated subckt.

    The old three-argument form `route(cell, layout, entry)` is still
    called, with cell=None. It only ever made sense when this ran at
    publication time, which is exactly the bug: by then route() has run
    and nothing the pycell adds will be drawn.
    """
    #- the plan carries the name; the CELL does not exist yet when this
    #- runs, and that is the point
    name = entry["name"]
    grp = subcell_groups(layout).get(entry["stack"])
    if grp is not None:
        #- ORDINARY POLYMORPHISM. The group IS the design's class and
        #- the base declares every phase, so these are method calls;
        #- there is nothing to look up and nothing to adapt.
        try:
            grp.beforePlace(entry)
        except Exception as e:
            log.error(f"{name}: beforePlace() raised: {e}")
        try:
            handled = bool(grp.beforeRoute(entry))
        except Exception as e:
            log.error(f"{name}: beforeRoute() raised: {e}")
            handled = False
        if handled:
            log.info(f"{name}: routed by its own pycell")
        return handled
    from cicpy.sidecar import import_beside
    dirname = getattr(layout, "dirname", "") or ""
    #- reload: the per-stack file is the one pycell edited between
    #- runs of the same process
    mod = import_beside(dirname, name, reload=True)
    if mod is None:
        return False
    hooks = {h: getattr(mod, h) for h in
             ("beforePlace", "beforeRoute", "route")
             if getattr(mod, h, None) is not None}
    return _invoke_stack_hooks(hooks, name, layout, entry, log, cell)


def _invoke_stack_hooks(hooks, name, layout, entry, log, cell=None):
    """Call a subcell's hooks by the standard pycell contract:

      beforePlace(layout, entry)   adjust the subcell's own stack;
                                   return value ignored
      beforeRoute(layout, entry)   route the subcell's internal
                                   nets; return True to mean "this
                                   subcell is ROUTED, the built-in
                                   router must not touch it". A
                                   stub that returns None leaves the
                                   built-in router in charge.
      route(cell, layout, entry)   the legacy name; its existence
                                   alone claims the subcell, because
                                   the one design shipping it relies
                                   on exactly that.
    """
    import inspect as _inspect
    bp = hooks.get("beforePlace")
    if bp is not None:
        try:
            bp(layout, entry)
        except Exception as e:
            log.error(f"{name}: pycell beforePlace() raised: {e}")
    br = hooks.get("beforeRoute")
    if br is not None:
        try:
            handled = bool(br(layout, entry))
            if handled:
                log.info(f"{name}: routed by its own pycell")
            return handled
        except Exception as e:
            log.error(f"{name}: pycell beforeRoute() raised: {e}")
            return False
    fn = hooks.get("route")
    if fn is None:
        return False
    try:
        nargs = len(_inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        nargs = 2
    try:
        if nargs >= 3:
            fn(cell, layout, entry)
        else:
            fn(layout, entry)
        log.info(f"{name}: routed by its own pycell")
        return True
    except Exception as e:
        log.error(f"{name}: pycell route() raised: {e}")
        return False


#- Schematics for the stack cells are NOT written from here, and an
#- attempt to do it was reverted. Driving XschemPrinter by hand from a
#- pycell hook does not work: symbolAndWrite RETURNS SILENTLY when a
#- referenced cell is missing from printer.cells
#- (xschemprinter.py:368), and at that point in the flow design.cells
#- holds exactly one cell -- the top. The result is a schematic with
#- every symbol and not one wire, which xschem then netlists as empty,
#- and LVS reports the CDL as having "no elements and/or nodes". No
#- warning is produced anywhere along that path.
#-
#- The stack cells are registered in the design, so they are in the
#- .cic, and the ordinary transpile writes them correctly because it
#- populates printer.cells as it iterates:
#-
#-   cicpy transpile <cell>.cic <tech> <LIB> --xschem --I <deps>
#-
#- 24 wires on a generated stack cell that way, against 0 by hand.


