"""The hierarchy, decided from the NETLIST and before any placement.

`plan_subcells` (core/subcell.py) answers the same question from a
PLACED layout: it reads the node graph and the instance objects, which
is why the hierarchical build has to place the cell flat first, publish
the subcells, write `<CELL>_HIER.spice`, and run a second process over
it. None of that is needed to know WHICH devices form a subcell and
WHICH nets cross its boundary. Both are properties of the netlist:

    membership   the design's own regex over instance names
    ports        a net is a port iff it is used outside this subcell --
                 by another subcell, by an instance no subcell claimed,
                 or by the parent, because it is in the parent's own
                 node list

That is the rule plan_subcells already uses (subcell.py:319-323), read
off `ckt.instances` instead of off geometry. Deciding it here means a
subcell can be BUILT as a cell in its own right -- placed from its own
origin, routed, published -- and the parent then instantiates it, in
one pass and one process.

What placement knows and a netlist does not: the fill devices
(`xfill_*`), which `fillDummyTransistors` creates during afterPlace and
which appear in no netlist. They cannot change a subcell's port list --
every terminal of a fill rides the subcell's own supply, and a supply
is already a port -- so the split computed here stays correct, and the
fills are added to the subcell's own netlist after it is placed.
"""
import logging
import re

log = logging.getLogger("Hierarchy")


def plan_from_netlist(ckt, specs, parent_name=None):
    """[{name, stack, instances, ports, internal, type}] from a netlist.

    `specs` is [{name, match, type}] in declaration order; the FIRST
    match wins, so a design reads specific to general. An instance no
    spec claims stays in the parent and counts as its own owner, which
    is what makes a net shared with it a port.
    """
    insts = list(getattr(ckt, "instances", []) or [])
    parent = (parent_name or getattr(ckt, "name", "") or "").upper()

    owner = {}
    for inst in insts:
        nm = getattr(inst, "name", "") or ""
        for s in specs:
            rx = s["match"]
            rx = rx if hasattr(rx, "search") else re.compile(rx)
            if rx.search(nm):
                owner[nm] = s["name"]
                break

    #- who touches each net: subcell names, and None for the parent's
    #- own leftovers. More than one owner means the net crosses out.
    touch = {}
    for inst in insts:
        o = owner.get(getattr(inst, "name", ""))
        for n in (getattr(inst, "nodes", []) or []):
            touch.setdefault(n, set()).add(o)

    parent_ports = set(getattr(ckt, "nodes", []) or [])

    members = {}
    for inst in insts:
        o = owner.get(getattr(inst, "name", ""))
        if o is not None:
            members.setdefault(o, []).append(inst)

    out = []
    for s in specs:
        mine = members.get(s["name"])
        if not mine:
            log.warning(f"{parent}: subcell {s['name']} claims no "
                        f"instances")
            continue
        nets = []
        for inst in mine:
            for n in (getattr(inst, "nodes", []) or []):
                if n not in nets:
                    nets.append(n)
        ports = sorted(n for n in nets
                       if len(touch.get(n, ())) > 1 or n in parent_ports)
        internal = sorted(n for n in nets if n not in ports)
        out.append({
            "name": f"{parent}_{s['name']}".upper(),
            "stack": s["name"],
            "type": s.get("type", "stack"),
            "instances": sorted(getattr(i, "name", "") for i in mine),
            "ports": ports,
            "internal": internal,
        })
    unclaimed = [getattr(i, "name", "") for i in insts
                 if getattr(i, "name", "") not in owner]
    if unclaimed:
        log.warning(f"{parent}: no subcell claims {len(unclaimed)} "
                    f"instance(s): {', '.join(sorted(unclaimed)[:8])}"
                    f"{' ...' if len(unclaimed) > 8 else ''}")
    return out


def split_subckt(ckt, plan):
    """Rewrite `ckt` in place: its devices leave for new subcircuits.

    Returns {subcell name: Subckt}. The parent keeps every instance no
    subcell claimed and gains one instance per subcell, named
    `x<stack>` -- the same name the generated `<CELL>_HIER.spice` used,
    so the sidecar's `rows` still address them.

    Not `Subckt.makeInstGroupSubckt` (cicspi/subckt.py:95), which has
    four defects for this purpose: it matches by `startswith` rather
    than by the design's regex, it exports the UNION of every member
    node rather than the boundary set, it leaves the parent's
    `inst_index` stale after removing from `instances`, and
    `SubcktInstance.fromSubckt` aliases the new instance's node list to
    the subckt's own port list.
    """
    import cicspi as spi

    parser = getattr(ckt, "parser", None)
    by_name = {getattr(i, "name", ""): i for i in ckt.instances}
    made = {}

    for entry in plan:
        sub = spi.Subckt(parser)
        sub.name = entry["name"]
        sub.nodes = list(entry["ports"])
        for nm in entry["instances"]:
            inst = by_name.get(nm)
            if inst is None:
                continue
            sub.addInstance(inst)
        if parser is not None:
            parser[sub.name] = sub
        made[entry["stack"]] = sub

    #- the parent keeps what no subcell took, then instantiates them
    taken = {nm for e in plan for nm in e["instances"]}
    kept = [i for i in ckt.instances
            if getattr(i, "name", "") not in taken]
    ckt.instances = kept
    _reindex(ckt)

    for entry in plan:
        sub = made[entry["stack"]]
        inst = spi.SubcktInstance(parser)
        inst.name = "x" + entry["stack"]
        inst.subcktName = sub.name
        #- a COPY: aliasing the parent's connection list to the child's
        #- port list makes editing one edit the other
        inst.nodes = list(entry["ports"])
        inst.groupName = inst.name
        ckt.addInstance(inst)
    return made


def _reindex(ckt):
    """Rebuild `inst_index` after the instance list changed.

    `addInstance` stores positional indices, and removing from
    `instances` without rebuilding leaves `getInstance` returning the
    wrong instance or running off the end.
    """
    ckt.inst_index = {}
    for i, inst in enumerate(ckt.instances):
        ckt.inst_index[getattr(inst, "name", "")] = i
