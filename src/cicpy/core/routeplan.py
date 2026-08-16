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
    """One subcell's conclusions as the paste-ready declaration.

    A COORDINATE IS NEVER WRITTEN. `anchored_options` turns a searched
    trunk into `trunkright`/`trunkleft`/`trunktab` whenever one of them
    resolves to exactly the lane the search chose; when none does, this
    used to fall back to `trunkx=<n>` and hand the design a number.
    That number survives neither a resize nor another technology, says
    nothing about why the wire is there, and -- because the fingerprint
    guarding a wires block is deliberately translation-invariant --
    replays silently against a placement it was never computed for.

    So the fallback refuses instead: the net comes out as a `blocked`
    triple naming the lane the search wanted and the anchors it was
    not. That is visible in every check, where a stale coordinate is
    visible in none, and it tells the designer exactly what to fix --
    move the pins until an anchor lands on that lane, or route the net
    by hand.
    """
    lines = [f"# class {stack}:",
             "    wires = ["]
    for e in entries:
        e = tuple(e)
        opts = e[3] if len(e) > 3 else ""
        m = re.search(r"trunkx=(-?[0-9.]+)", opts or "")
        if m and len(e) > 3:
            e = (e[0], "blocked",
                 f"the search put this trunk at {int(float(m.group(1)))}, "
                 f"which is not a pin anchor -- and a coordinate is not "
                 f"written into a design. Move the pins so trunkright/"
                 f"trunkleft/trunktab lands on that lane, or route it "
                 f"by hand.")
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


#- --------------------------------------------------------------------
#- searched polylines, given back as STORIES
#- --------------------------------------------------------------------
#- The search already emits paths -- Path.fromNodes turns its node list
#- into drawn geometry -- but their corners are coordinates, and a
#- coordinate may not enter a design file. This is the last mile: each
#- corner is resolved back to something the design can NAME -- a pin of
#- the net (plus whole PITCHes), or a track of a registered channel
#- (plus a SPACE) -- and the whole route is written to <CELL>.routes.py
#- as a paste-ready `paths` entry. A corner that resolves to nothing is
#- written as UNANCHORED, loudly, so the suggestion is a draft to
#- finish and not a number smuggled in through a comment.
#-
#- This is the same discipline anchored_options applies to a straight
#- trunk, extended to an arbitrary polyline; PWRUP_B_1V8 in LELO_TEMP
#- was exactly this process done by hand, and is the shape of output
#- this aims to produce.

def _grid(cell):
    try:
        from .gridcheck import gridFromRules
        from .rules import Rules
        return gridFromRules(Rules.getInstance()) or 50
    except Exception:
        return 50


def _net_pins(cell, net):
    """[(instanceName, rect)] of every published pin of `net`."""
    out = []
    for inst in cell.iterInstances():
        nm = getattr(inst, "instanceName", "") or ""
        for ch in getattr(inst, "children", []) or []:
            if (getattr(ch, "isPort", lambda: False)()
                    and getattr(ch, "name", "") == net):
                r = ch.get() if hasattr(ch, "get") else None
                if r is not None:
                    out.append((nm, r))
    return out


def _anchor_coord(cell, net, coord, axis, pins):
    """One coordinate as the anchor that reproduces it, or None.

    Preference order is meaning, not distance: a pin of the net says
    WHY the wire is there, a channel track says WHERE the floorplan
    allows it, and an offset in whole PITCHes or one SPACE keeps
    either honest. Anything else is not an anchor.
    """
    pitch = cell._lanePitch(None)
    #- a QUARTER LANE, not the manufacturing grid. The search walks its
    #- own grid, which is finer than a lane, so a corner lands NEAR the
    #- track or pin that explains it rather than on it -- measured on
    #- LELO_TEMP's PWRUP_B, 400 units off dband track 0 and 1400 off
    #- the strip pin it was landing on, both refused at grid tolerance.
    #- A quarter lane still cannot confuse two neighbouring tracks.
    tol = max(_grid(cell), pitch // 4)
    space = 0
    try:
        from .rules import Rules
        space = int(Rules.getInstance().get("M4", "space"))
    except Exception:
        pass
    #- the net's own pins first, exact then in whole PITCHes
    for nm, r in pins:
        c = int(r.centerX()) if axis == "x" else int(r.centerY())
        d = coord - c
        if abs(d) <= tol:
            return f'pin("{nm}", "{net}", "{axis}")'
        k = round(d / pitch)
        if k != 0 and abs(k) <= 4 and abs(d - k * pitch) <= tol:
            sign = "+" if k > 0 else "-"
            return (f'pin("{nm}", "{net}", "{axis}") {sign} '
                    f'{abs(k)} * PITCH')
    #- then the registered channels: a vertical channel anchors an x,
    #- a horizontal one a y (channelTrackCoord: lo + (i + 0.5) * pitch)
    for name, (lo, hi, horizontal) in sorted(
            (getattr(cell, "_routing_channels", {}) or {}).items()):
        if horizontal == (axis == "x"):
            continue
        for extra, suffix in ((0, ""), (space, " + SPACE"),
                              (-space, " - SPACE")):
            f = (coord - extra - lo) / pitch - 0.5
            i = round(f)
            if i < 0 or i >= max(1, int((hi - lo) // pitch)):
                continue
            if abs(coord - extra - (lo + (i + 0.5) * pitch)) <= tol:
                return f'track("{name}", {i}){suffix}'
    return None


def _end_name(cell, rect, net):
    """(instanceName, net) of the pin `rect` is, or None."""
    if rect is None:
        return None
    for nm, r in _net_pins(cell, net):
        if (abs(int(r.x1) - int(rect.x1)) < 2 and
                abs(int(r.y1) - int(rect.y1)) < 2):
            return nm
    return None


def path_suggestion(cell, net, links):
    """One searched net as a paste-ready `paths` entry, as text.

    `links` is [(a_rect, b_rect, nodes)] -- what the search proved,
    link by link. Returns (text, unanchored_count).
    """
    from .path import simplify
    lines = []
    unanchored = 0
    for a, b, nodes in links:
        corners = simplify(nodes)
        if len(corners) < 2:
            continue
        pins = _net_pins(cell, net)
        an = _end_name(cell, a, net)
        bn = _end_name(cell, b, net)
        head = f'        dict(net="{net}"'
        if an and bn:
            head += (f',\n             start=("{an}", "{net}"),'
                     f' stop=("{bn}", "{net}")')
        lines.append(head + ",")
        lines.append("             steps=[")
        cur = corners[0]
        order = {"M1": 0, "M2": 1, "M3": 2, "M4": 3, "M5": 4}
        for nxt in corners[1:]:
            if nxt[2] != cur[2]:
                #- the declarative form spells a layer change as the
                #- direction it goes, with the target named -- there is
                #- no "layer" step a design file can call
                word = ("up" if order.get(nxt[2], 0) > order.get(cur[2], 0)
                        else "down")
                lines.append(f'                    ("{word}", "{nxt[2]}"),')
            for axis, idx in (("x", 0), ("y", 1)):
                if nxt[idx] == cur[idx]:
                    continue
                anch = _anchor_coord(cell, net, int(nxt[idx]), axis, pins)
                if anch is None:
                    unanchored += 1
                    lines.append(
                        f'                    #- UNANCHORED: the search '
                        f'chose {axis}={int(nxt[idx])} and no pin or '
                        f'channel reproduces it. Name a channel there, '
                        f'or move the pins.')
                    lines.append(
                        f'                    ("move{axis}", None),  '
                        f'#- {axis}={int(nxt[idx])}')
                else:
                    lines.append(
                        f'                    ("move{axis}", {anch}),')
            cur = nxt
        lines.append('                    ("end",)]),')
    return "\n".join(lines), unanchored


def write_path_suggestions(layout, net, links, log=log):
    """Append a `paths` suggestion for a searched net to
    <routes_owner>.routes.py, beside the wires suggestions."""
    dirname = getattr(layout, "dirname", "") or ""
    name = getattr(layout, "name", "") or ""
    if not dirname or not name or not links:
        return
    text, unanchored = path_suggestion(layout, net, links)
    if not text:
        return
    owner = getattr(layout, "routes_owner", "") or name
    path = os.path.join(dirname, owner + ".routes.py")
    state = ("NOT paste-ready: finish the UNANCHORED steps first"
             if unanchored else "paste-ready")
    block = (f"\n#- SEARCHED route for {net}, told as a story "
             f"({state}).\n"
             f"#- Add to a `paths` declaration and gate with "
             f"paths_only while verifying.\n"
             f"{text}\n")
    try:
        with open(path, "a") as f:
            f.write(block)
    except Exception as e:
        log.warning(f"{path}: could not write path suggestion: {e}")
        return
    log.info(f"{net}: searched route written to {path} as a paths "
             f"entry ({state})")
