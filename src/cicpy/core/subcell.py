#- --------------------------------------------------------------------
#- Subcell publication
#- --------------------------------------------------------------------
#- How a flat stack layout becomes published subcells: the plan that
#- names them (plan_subcells / subcell_spec / subcell_membership /
#- subcell_groups), the netlist each publishes (stack_subckt), their
#- per-stack pycell hooks (run_stack_pycells), and the writer that
#- copies the geometry out under each name (write_stack_cells).
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

    def _walk(grp):
        #- marked by the design: it is a subcell whatever it is made of
        if getattr(grp, "subcell", False):
            _claim(grp, getattr(grp, "name", ""))
            return
        if isinstance(grp, StackGroup):
            _claim(grp, getattr(grp, "name", ""))
            return  #- below a stack is routing, not placement
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                _walk(c)

    #- the groups fill in around the sidecar, never over it: _claim
    #- respects an instance the sidecar already took
    for grp in getattr(layout, "cellgroups", []) or []:
        _walk(grp)
    return member


#- the old name, kept because it reads correctly wherever the subcell
#- IS a stack, which is still the common case
stack_membership = subcell_membership


def subcell_groups(layout):
    """{subcell name: the CellGroup itself}.

    The group, not just its instance names, because
    CellGroup.addConnectivityRoute scopes itself -- it builds its own
    instanceRegex and takes a different path through getNodeAccessRects
    than passing includeInstances by hand does. The hand written routes
    that worked all went through the group.

    Same rule as subcell_membership: a group the design marked, else a
    StackGroup. Keep the two in step or the router will be handed a
    name it cannot find a group for.
    """
    from cicpy.core.cellgroup import CellGroup, StackGroup
    out = {}

    def _walk(grp):
        if getattr(grp, "subcell", False) or isinstance(grp, StackGroup):
            nm = getattr(grp, "name", "")
            if nm:
                out[nm] = grp
            return
        for c in getattr(grp, "children", []) or []:
            if isinstance(c, (StackGroup, CellGroup)):
                _walk(c)

    for grp in getattr(layout, "cellgroups", []) or []:
        _walk(grp)
    return out


stack_groups = subcell_groups


def run_stack_pycells(layout, log=None):
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
        plan = plan_stack_cells(layout)
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
    member = stack_membership(layout)

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

      1. its Subcell class in the <CELL>.py sidecar -- beforePlace /
         beforeRoute / route written inline, without self, beside the
         declaration they belong to. See cicpy/sidecar.py.
      2. its own <STACKCELL>.py beside the design -- same lookup as
         cic.py's, dirname + name + ".py" on sys.path. The escape
         hatch for a subcell whose routing outgrows the sidecar file.

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
    import importlib
    import os
    import sys
    #- the plan carries the name; the CELL does not exist yet when this
    #- runs, and that is the point
    name = entry["name"]
    cls = (getattr(layout, "_sidecar_classes", None) or {}).get(
        entry["stack"])
    if cls is not None:
        from cicpy.sidecar import hooks_of
        hooks = hooks_of(cls)
        if hooks:
            return _invoke_stack_hooks(hooks, name, layout, entry,
                                       log, cell)
    dirname = getattr(layout, "dirname", "") or ""
    path = os.path.join(dirname, name + ".py")
    if not os.path.exists(path):
        return False
    if dirname not in sys.path:
        sys.path.append(dirname)
    try:
        mod = importlib.import_module(name)
        importlib.reload(mod)
    except Exception as e:
        log.error(f"{name}: pycell failed to import: {e}")
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


def write_stack_cells(layout, design=None, plan=None, log=None):
    """Register each stack as a real cell so a .mag is written for it.

    Returns [(name, fingerprint, ports)].

    This is the standalone-verification step, and deliberately NOT the
    restructuring one. The parent keeps its instances; each stack is
    additionally published as a cell holding the same instances, with
    its boundary nets as ports. That is enough to get a .mag and a
    netlist per stack and to LVS each one ALONE -- which is the gate the
    hierarchy needs -- without disturbing a parent that currently works.

    Turning the parent into a cell that REFERENCES these rather than
    containing them is a separate change, and it should not be made
    until the standalone LVS passes: it is the difference between
    "generate and check" and "generate, check, and rely on".
    """
    from cicpy.core.layoutcell import LayoutCell
    log = log or logging.getLogger("MazeRouter")
    design = design if design is not None else design_of(layout)
    if design is None:
        log.warning("no design reachable from the layout; no stack cells written")
        return []
    plan = plan if plan is not None else plan_stack_cells(layout)
    made = []
    for entry in plan:
        name = entry["name"]
        if name in getattr(design, "cells", {}):
            continue
        cell = LayoutCell()
        cell.name = name
        cell.design = design
        #- Bound from the INSTANCES, not from every rect, so a route
        #- drawn inside a stack cannot inflate the placement box.
        #-
        #- It does NOT explain the size, and that was measured before
        #- assuming it did. A stack is as wide as the device columns it
        #- holds plus the library's guard: one column plus its ring,
        #- and twice that for two columns. The overhang is the guard
        #- ring a cell carries past its own box so that abutted columns
        #- MERGE their guards -- shared in the parent, and paid in full
        #- by a stack standing alone. The size is right; nothing to trim.
        #-
        #- Normalised to the origin below, like any library cell: a
        #- placeable cell whose content starts at the parent's absolute
        #- offset is only placeable at one position. The offset it was
        #- cut from is kept on the cell as `placed_at`, which is where
        #- a hierarchical parent puts its instance.
        cell.boundaryIgnoreRouting = True
        #- the bbox check reads ignoreBoundaryRouting (set through
        #- setBoundaryIgnoreRouting); assigning the attribute above
        #- shadowed the method and never reached the check
        cell.setBoundaryIgnoreRouting(True)
        wanted = set(entry["instances"])
        for inst in layout.iterInstances():
            if (getattr(inst, "instanceName", "") or "") in wanted:
                cell.add(inst)
        #- The routing that belongs to this stack. Without it the cell
        #- holds devices and no wires, so its layout extracts as one net
        #- per terminal: measured on P_IN_A, 7 devices and 22 nets
        #- against the schematic's 5 -- with the DEVICE count matching
        #- exactly, which is how it was clear the decomposition was
        #- right and only the wires were missing.
        #-
        #- A stack's routing is the geometry inside its own bounds,
        #- which is what a stack-level router would produce and what the
        #- parent currently produces. Copies, not moves: the parent
        #- still needs its geometry, and this cell is published
        #- alongside it rather than replacing it.
        cell.updateBoundingRect()
        #- ...inside its own bounds PLUS the guard overhang. The ring a
        #- cell carries past its box is still its own geometry, and a
        #- route landing on it (a supply hop to the ring stub) was
        #- silently dropped by the tight test: drawn in the parent,
        #- cuts and all, and absent from the published cell. 4800 is
        #- the tiling's shared-guard margin.
        _g = 4800
        sx1, sy1, sx2, sy2 = cell.x1 - _g, cell.y1 - _g, cell.x2 + _g, cell.y2 + _g
        #- The parent's ROUTING, and only that. Not
        #- _collectPhysicalRects: that flattens instance content too, so
        #- copying it duplicates every device's own geometry, which the
        #- instances already bring. Routed wires are not direct children
        #- either -- they live inside Route objects -- so this walks the
        #- non-instance children and takes the rects it finds.
        _seen = set()

        def _routed(node, out, depth=0):
            if depth > 6:
                return
            #- dedup APPENDED leaves only. Marking every visited node
            #- made the second pass (over layout.routes) return at the
            #- door for any route already seen as a layout child, and
            #- its wires were never collected -- the published cells
            #- lost all their metal, measured.
            for ch in getattr(node, "children", []) or []:
                if ch is None or id(ch) in _seen:
                    continue
                #- ...except a via, which IS an instance. Skipping every
                #- instance dropped the cuts and left the wires floating
                #- over the pins they were supposed to land on: opens in
                #- LVS and enclosure errors in DRC, from a stack whose
                #- wires all looked present.
                if hasattr(ch, "isInstance") and ch.isInstance():
                    if type(ch).__name__ == "InstanceCut":
                        _seen.add(id(ch))
                        out.append(ch)
                    continue
                if hasattr(ch, "isPort") and ch.isPort():
                    continue
                #- containers answer isRect() too, and appending one
                #- publishes its BBOX as a layerless rect (a Route's
                #- landed inside a window after a resize -- 26 DRC
                #- errors from one blob). Their content arrives by the
                #- dedicated paths: routes via layout.routes below,
                #- dummy ties via the group walk.
                if getattr(ch, "children", None):
                    continue
                if hasattr(ch, "isRect") and ch.isRect():
                    _seen.add(id(ch))
                    out.append(ch)
                else:
                    _routed(ch, out, depth + 1)

        routed = []
        _routed(layout, routed)
        #- The dummy supply ties live in stack.children, behind a
        #- CellGroup that answers isRect() and so ends the walk above.
        #- Collect exactly them -- and ONLY them: publishing the rest
        #- of a stack's route children duplicates geometry the parent
        #- draws itself (its drops land cuts on the same pins), which
        #- is a partial via overlap in the assembled top, measured.
        def _dummy_ties(grp):
            for r in getattr(grp, "dummy_routes", []) or []:
                if id(r) not in _seen:
                    _seen.add(id(r))
                    routed.append(r)
            for sub in getattr(grp, "stacks", []) or []:
                _dummy_ties(sub)
        for grp in getattr(layout, "cellgroups", []) or []:
            _dummy_ties(grp)
        #- and the ROUTES, which are not in children. Walking children
        #- alone found 32 rects in the whole parent -- the li tabs and
        #- nothing else -- so a stack cell came out with its devices and
        #- none of the wires between them, and LVS saw six unconnected
        #- transistors.
        for r in getattr(layout, "routes", []) or []:
            _routed(r, routed)
        added = vias = 0
        for r in routed:
            if not (r.x1 >= sx1 and r.x2 <= sx2
                    and r.y1 >= sy1 and r.y2 <= sy2):
                continue
            #- A VIA IS NOT A RECT and getCopy() flattens it into one:
            #- Rect.getCopy returns a bare Rect, so a copied InstanceCut
            #- lost its class and its cut cell and the subcell came out
            #- with wires floating over the pins they land on. Clone it
            #- as what it is -- the cut cell reference and the position
            #- are the whole of its state.
            if type(r).__name__ == "InstanceCut":
                from cicpy.core.instancecut import InstanceCut
                c2 = InstanceCut()
                c2.name = getattr(r, "name", "")
                c2.cell = getattr(r, "cell", "") or c2.name
                c2.instanceName = getattr(r, "instanceName", "") or c2.name
                c2.layer = getattr(r, "layer", "")
                for attr in ("_cell_obj", "layoutcell", "design"):
                    if getattr(r, attr, None) is not None:
                        setattr(c2, attr, getattr(r, attr))
                c2.setRect(r)
                cell.add(c2)
                vias += 1
                continue
            rr = r.getCopy()
            rr.is_routing = True
            cell.add(rr)
            added += 1
        log.info(f"{name}: {added} routed rects and {vias} vias "
                 f"of {len(routed)} inside")

        #- The boundary nets, as ports -- and WHICH pin becomes the
        #- port is decided by the rest of the net. Every pin of the net
        #- OUTSIDE this subcell is an anchor; their centroid is the
        #- centre of the net's graph; the inside pin NEAREST that
        #- centre is the port. Before this the first pin found won,
        #- which put ports wherever iteration order left them -- the
        #- port is the one thing the parent routes to, and it should
        #- face the traffic. A net with no outside pins (the parent's
        #- own IO living wholly in one subcell) keeps the first pin.
        pins = {}
        supplies = supply_nets(layout)
        for net in entry["ports"]:
            g = layout.nodeGraph.get(net)
            if g is None:
                continue
            inside, anchors, bulks = [], [], []
            for port in getattr(g, "ports", []):
                pinst = getattr(port, "parent", None)
                nm = getattr(pinst, "instanceName", "") if pinst else ""
                rect = port.get() if hasattr(port, "get") else None
                if rect is None:
                    continue
                (inside if nm in wanted else anchors).append(rect)
                if nm in wanted and getattr(port, "childName", "") == "B":
                    bulks.append(rect)
            if not inside:
                continue
            #- A supply port sits on the BULK geometry at the row
            #- boundary -- ground on the lowest rect, power on the
            #- highest -- which is the guard column, continuous
            #- through the tap row. A parent ring then connects with
            #- a straight stretch through pure guard, and the pin
            #- layer over the stack stays free.
            if net in supplies:
                #- a supply port is a BULK rect when the devices offer
                #- one: the guard/tap column, which is what a parent
                #- ring connects through. The strap is a source pin
                #- and belongs to the device, not the boundary.
                cands = bulks or inside
                if re.search("VSS|GND", net):
                    pr = min(cands, key=lambda r: r.y1)
                else:
                    pr = max(cands, key=lambda r: r.y2)
                #- clipped to the pre-copy box: the bulk columns
                #- straddle the cell edge, and a port poking past the
                #- box inflates it, shifting the published origin by
                #- the overhang -- every parent-tuned track then lands
                #- 4800 off its pin (measured).
                pr = pr.getCopy()
                pr.x1 = max(pr.x1, sx1 + _g)
                pr.x2 = min(pr.x2, sx2 - _g)
                pr.y1 = max(pr.y1, sy1 + _g)
                pr.y2 = min(pr.y2, sy2 - _g)
                pins[net] = pr
                continue
            if anchors:
                cx = sum(r.centerX() for r in anchors) / len(anchors)
                cy = sum(r.centerY() for r in anchors) / len(anchors)
                pins[net] = min(inside,
                                key=lambda r: (abs(r.centerX() - cx)
                                               + abs(r.centerY() - cy)))
            else:
                pins[net] = inside[0]
        for net, rect in pins.items():
            try:
                cell.addPort(net, rect)
            except Exception as e:
                log.warning(f"{name}: could not add port {net}: {e}")
        cell.updateBoundingRect()
        #- NOT normalised to the origin, and the reason is structural:
        #- this cell holds the PARENT'S OWN instance objects, not
        #- copies, so translating it drags the parent's devices with it
        #- -- measured, 2 shorts and 23 DRC in a top that was clean.
        #- Origin-normalisation belongs to the restructuring step where
        #- the instances genuinely move out of the parent. Until then
        #- placed_at records the offset a hierarchical parent needs.
        cell.placed_at = (int(cell.x1), int(cell.y1))
        lines, fp = stack_subckt(layout, entry)
        cell.cic_subckt = lines
        cell.cic_fingerprint = fp
        #- Give the cell a real Subckt, parsed from the generated text.
        #- Subckt.parse takes spice lines, so the generated netlist and
        #- the object the printers want are the same thing rather than
        #- two representations to keep in step.
        try:
            from cicspi import Subckt
            #- the PARENT's parser. A Subckt built without one has no
            #- instance registry to resolve subcircuit references
            #- against, and parse() dies on the first device with
            #- "NoneType has no attribute allinst".
            parser = getattr(getattr(layout, "ckt", None), "parser", None)
            if parser is None:
                parser = getattr(Subckt, "circuits", None)
            ckt = Subckt(parser)
            ckt.parse(list(lines), 0)
            cell.ckt = ckt
        except Exception as e:
            log.warning(f"{name}: could not build a subckt: {e}")
        design.cells[name] = cell
        if hasattr(design, "cellnames") and name not in design.cellnames:
            #- ahead of the parent, so it is defined before it is used
            design.cellnames.insert(0, name)
        #- The pycell is NOT run here. It used to be, and that made it
        #- dead: this is afterPaint, route() ran long ago, and any Route
        #- the pycell added was never drawn. It runs before beforeRoute
        #- now -- see run_stack_pycells.
        made.append((name, fp, sorted(pins)))
        log.info(f"stack cell {name}: {len(wanted)} instances, "
                 f"{len(pins)} ports, fp={fp}")
    return made


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


