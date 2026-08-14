"""Wires in the sidecar: the maze router's conclusions, hand-owned.

The stack-level router spends its time DECIDING -- track maps and an
A* search per net -- and hands the drawing to route.py as one
`addConnectivityRoute` command per net (measured: the deciding was
23.9 s of a 24.1 s build). The decision belongs in the design, where
it can be read and edited: a subcell class in the `<CELL>.py` sidecar
declares it as

    class p_bias(Stack):
        ...
        wires = [
            ("VD1", "M1", "||", "trunkx=233200"),
            ("VBP", "M2", "-|--", ""),
            ("VSU", "blocked", "pins share only -9600 of column..."),
        ]
        wires_key = "1a2b3c4d5e6f"

Each 4-tuple is (net, layer, routeType, options) -- ordinary
addConnectivityRoute arguments, edited like any other route -- and a
("net", "blocked", reason) triple records a net the search proved
unroutable, so replay reproduces the outcome instead of quietly
retrying it. route_stack_level replays declared nets and searches
only what is undeclared.

The options are RESOLVED (a trunkx is a coordinate), so the block is
only as good as the placement it was computed against: `wires_key`
fingerprints the stack's own instances, and on any mismatch the
whole block is ignored -- loudly -- and the router searches afresh.
Every searched stack's conclusions are written to
`<CELL>.routes.py` beside the design as a paste-ready block: run the
build once, read that file, put the blocks into the sidecar.

CICPY_NO_ROUTEPLAN=1 ignores every wires declaration.
"""
import hashlib
import logging
import os
import re

log = logging.getLogger("RoutePlan")


def stack_key(instances):
    """The fingerprint of a stack's own ARRANGEMENT: every member's
    name, cell and position RELATIVE to the stack's own corner.

    Relative, because the question a wires block asks is "are these
    the same devices in the same arrangement", and that is a property
    of the stack alone. Hashing absolute coordinates answered a
    different question -- "is this stack still in the same place in
    its parent" -- so a block went stale when a neighbouring column
    changed width, and every subcell's block would go stale the day
    subcells are placed from their own origin.
    """
    insts = [i for i in instances if i is not None]
    if not insts:
        return hashlib.sha1(b"[]").hexdigest()[:12]
    ox = min(int(i.x1) for i in insts)
    oy = min(int(i.y1) for i in insts)
    rows = sorted((getattr(i, "instanceName", ""),
                   getattr(i, "cell", ""), int(i.x1) - ox, int(i.y1) - oy)
                  for i in insts)
    return hashlib.sha1(repr(rows).encode()).hexdigest()[:12]


def wires_lookup(entry, key, instances=()):
    """{net: wire tuple} of a subcell's declared wires, or None.

    None when nothing is declared, replay is disabled, or the
    declared wires_key does not match the placement fingerprint --
    the last one warns, because silently replaying stale coordinates
    is the one thing this must never do.

    And the key alone cannot see it. The fingerprint is deliberately
    translation-invariant -- it asks "the same devices in the same
    arrangement", which is a property of the stack -- while a
    resolved `trunkx` is an ABSOLUTE coordinate. Move the stack and
    every key still matches while every trunk is off by the
    translation. So the coordinates are checked against the stack
    they claim to be inside: a trunk outside its own devices is not a
    stale block that can be replayed carefully, it is a wire in
    another cell.
    """
    wires = entry.get("wires") if entry else None
    if not wires or os.environ.get("CICPY_NO_ROUTEPLAN"):
        return None
    declared = entry.get("wires_key", "")
    #- A mismatch condemns the COORDINATES, not the whole block.
    #-
    #- What goes stale is a resolved trunkx or bandy: an absolute number
    #- that meant something only against the placement it was computed
    #- from. An anchor does not -- trunktab/trunkright/trunkleft are
    #- recomputed from the net's own pins every run -- and a `blocked`
    #- declaration carries no geometry at all, it only says this net is
    #- not for the maze router to draw.
    #-
    #- Throwing those away with the coordinates is what made renaming
    #- instances expensive: the fingerprint covers every member's name,
    #- so collapsing a fill run to a vector instance invalidated a whole
    #- block, the router searched, and in LELOTEMP_BIAS_IBP's p_su it
    #- then shorted VDD_1V8 to VSU -- the very thing the block's three
    #- `blocked` lines existed to prevent.
    stale = declared != key
    if stale:
        log.warning(f"{entry.get('name', '?')}: wires_key {declared!r} "
                    f"does not match the placement ({key}); any wire "
                    f"declaring a coordinate is dropped and searched "
                    f"afresh, the rest replay")
    insts = [i for i in (instances or []) if i is not None]
    span = None
    if insts:
        #- one device of slack each side: a trunk just beside the
        #- column is ordinary, a trunk a column away is not
        slack = max(int(i.x2 - i.x1) for i in insts)
        span = (min(int(i.x1) for i in insts) - slack,
                max(int(i.x2) for i in insts) + slack)
    out = {}
    for w in wires:
        if len(w) < 2:
            continue
        if stale:
            #- the coordinate-bearing ones, and only those
            if len(w) >= 4 and re.search(r"(trunkx|bandy)=?-?\d",
                                         str(w[3]) or ""):
                log.warning(
                    f"{entry.get('name', '?')}: {w[0]} declares a "
                    f"coordinate against a placement that has changed "
                    f"-- searching this net afresh")
                continue
        if span is not None and len(w) >= 4:
            m = re.search(r"trunkx=(-?[0-9.]+)", str(w[3]) or "")
            if m and not (span[0] <= float(m.group(1)) <= span[1]):
                log.error(
                    f"{entry.get('name', '?')}: {w[0]} declares "
                    f"trunkx={m.group(1)}, which is outside the "
                    f"stack's own {span[0]}..{span[1]}. The block was "
                    f"resolved against another placement -- searching "
                    f"this net afresh.")
                continue
        out[str(w[0])] = tuple(w)
    return out


def _cut_counts(opts):
    """The (horizontal, vertical) cut array a wire's options ask for.

    Same defaults as Route (`core/route.py`): `<N>cuts` and `<N>vcuts`,
    2x1 when the options say nothing.
    """
    m = re.search(r"(\d+)cuts", opts or "")
    mv = re.search(r"(\d+)vcuts", opts or "")
    return (int(m.group(1)) if m else 2, int(mv.group(1)) if mv else 1)


def replay_claims(rects, layer, pin_layer, opts):
    """The claims a replayed wire makes, recomputed from its pins.

    Only mixed stacks need them -- a net still searching must avoid
    the lanes and landings a replayed neighbour has spoken for -- and
    they are recomputable: the trunk from the resolved trunkx over
    the pins' span, a landing per pin when the wire vias off the pin
    layer.
    """
    claims = []
    ys = ([int(r.y1) for r in rects] + [int(r.y2) for r in rects])
    m = re.search(r"trunkx=(-?[0-9.]+)", opts or "")
    if m and ys:
        claims.append((int(float(m.group(1))), min(ys), max(ys)))
    if layer and pin_layer and layer != pin_layer:
        #- the cut the route will ACTUALLY draw, which is a 2x1 by
        #- default (route.py: cuts=2, vcuts=1). Sizing the claim off a
        #- 1x1 under-reserved every landing pad by a cut's width, so a
        #- net still searching was told a replayed neighbour needed
        #- less room than it takes.
        pad_w = 0
        try:
            from .cut import Cut
            hc, vc = _cut_counts(opts)
            ct = (Cut.getInstance(pin_layer, layer, hc, vc)
                  or Cut.getInstance(layer, pin_layer, hc, vc)
                  or Cut.getInstance(pin_layer, layer, 1, 1)
                  or Cut.getInstance(layer, pin_layer, 1, 1))
            if ct is not None:
                pad_w = int(max(ct.width(), ct.height()))
        except Exception:
            pass
        for pr in rects:
            claims.append((int((pr.x1 + pr.x2) // 2),
                           int(pr.y1) - pad_w, int(pr.y2) + pad_w,
                           int((pr.x2 - pr.x1) // 2 + pad_w // 2)))
    return claims


def format_wires_block(stack, entries, key):
    """One subcell's conclusions as the paste-ready declaration."""
    lines = [f"# class {stack}:",
             "    wires = ["]
    for e in entries:
        lines.append("        " + repr(tuple(e)) + ",")
    lines.append("    ]")
    lines.append(f'    wires_key = "{key}"')
    return "\n".join(lines)


def write_suggestions(layout, captured_by_stack, keys_by_stack):
    """The searched stacks' conclusions, as paste-ready blocks in
    `<CELL>.routes.py` beside the design.

    <CELL> is the cell whose SIDECAR declares the subcell, which is
    not always the cell being routed: a subcell is built as a cell of
    its own now, and its blocks belong in its parent's file, where
    its class is. `routes_owner` names that cell, and the parent
    clears the file before it builds anything, so one run's blocks
    accumulate and the previous run's do not survive it.
    """
    if not captured_by_stack:
        return
    dirname = getattr(layout, "dirname", "") or ""
    name = getattr(layout, "name", "") or ""
    if not dirname or not name:
        return
    owner = getattr(layout, "routes_owner", "") or name
    path = os.path.join(dirname, owner + ".routes.py")
    blocks = []
    if not os.path.exists(path):
        blocks.append(
            f"#- ROUTER-GENERATED wires for {owner}. Paste each block\n"
            f"#- into its subcell class in {owner}.py; the build then\n"
            f"#- replays them instead of searching. This file is\n"
            f"#- scratch output, rewritten by every searched build.")
    for stack in sorted(captured_by_stack):
        blocks.append(format_wires_block(
            stack, captured_by_stack[stack], keys_by_stack.get(stack, "")))
    try:
        with open(path, "a") as f:
            f.write("\n\n".join(blocks) + "\n")
    except Exception as e:
        log.warning(f"{path}: could not write wire suggestions: {e}")
        return
    log.info(f"route conclusions for {len(captured_by_stack)} "
             f"stack(s) written to {path}; paste the blocks into "
             f"{owner}.py to replay them")
