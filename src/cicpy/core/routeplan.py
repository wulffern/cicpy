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


def wires_lookup(entry, key):
    """{net: wire tuple} of a subcell's declared wires, or None.

    None when nothing is declared, replay is disabled, or the
    declared wires_key does not match the placement fingerprint --
    the last one warns, because silently replaying stale coordinates
    is the one thing this must never do.
    """
    wires = entry.get("wires") if entry else None
    if not wires or os.environ.get("CICPY_NO_ROUTEPLAN"):
        return None
    declared = entry.get("wires_key", "")
    if declared != key:
        log.warning(f"{entry.get('name', '?')}: wires_key {declared!r} "
                    f"does not match the placement ({key}); the wires "
                    f"block is stale -- searching afresh")
        return None
    out = {}
    for w in wires:
        if len(w) >= 2:
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
    `<CELL>.routes.py` beside the design."""
    if not captured_by_stack:
        return
    dirname = getattr(layout, "dirname", "") or ""
    name = getattr(layout, "name", "") or ""
    if not dirname or not name:
        return
    path = os.path.join(dirname, name + ".routes.py")
    blocks = [f"#- ROUTER-GENERATED wires for {name}. Paste each block\n"
              f"#- into its subcell class in {name}.py; the build then\n"
              f"#- replays them instead of searching. This file is\n"
              f"#- scratch output, rewritten by every searched build."]
    for stack in sorted(captured_by_stack):
        blocks.append(format_wires_block(
            stack, captured_by_stack[stack], keys_by_stack.get(stack, "")))
    try:
        with open(path, "w") as f:
            f.write("\n\n".join(blocks) + "\n")
    except Exception as e:
        log.warning(f"{path}: could not write wire suggestions: {e}")
        return
    log.info(f"route conclusions for {len(captured_by_stack)} "
             f"stack(s) written to {path}; paste the blocks into "
             f"{name}.py to replay them")
