"""Placement from the sidecar alone.

The <CELL>.yaml sidecar already declares WHAT the subcells are; with
`order` per subcell and `rows` for the floorplan it declares the whole
placement, and this module is the recipe that executes it:

    stacks (in declared member order) -> taps and dummy fill ->
    rows abutted left to right, stacked bottom to top -> a routing
    channel between the rows and one per column -> supply rings and
    guard connections -> the stack-level router -> publish.

A <CELL>.py pycell still wins when it exists: a file is for the cell
that needs something the recipe cannot say. The sidecar is for the
cell that does not.

Schema (all placement keys optional; their presence enables this):

    place:      {groupbreak: 6, channel: 6}          # channel in um
    subcells:
      - name: p_bias
        match: '...'          # as before: membership for publication
        type: stack
        group: pmos           # placement group (fill+taps per group)
        order: ['xba1', 'xba8', ...]   # fullmatch patterns, in order
        channel: bias         # vertical channel name (default: name)
    rows:
      - [n_load_a, n_load_b, n_mirr, r_deg]          # bottom row
      - [p_in_a, p_in_b, p_bias, p_sw]
    supplies:
      - {net: VDD_1V8, ring: t, guard_exclude: '^xbs6$', strap: top}
      - {net: VSS, ring: b, strap: bottom, strap_exclude: '...'}
"""
import re
import logging

log = logging.getLogger("SidecarPycell")


def has_placement(spec):
    return bool(spec) and "rows" in spec and "subcells" in spec


class SidecarPycell:
    """A pycell built from the sidecar. Quacks like the module."""

    def __init__(self, spec):
        self.spec = spec
        self.data = {"afterPaint": [{"resetOrigins": [[1]]}]}

    # -- hooks -------------------------------------------------------

    def beforePlace(self, layout):
        p = self.spec.get("place", {})
        layout.noPowerRoute = True
        layout.place_xspace = [p.get("xspace", 0)]
        layout.place_yspace = [p.get("yspace", 0)]
        layout.place_groupbreak = [p.get("groupbreak", 10)]

    def afterPlace(self, layout):
        spec = self.spec
        p = spec.get("place", {})
        channel = p.get("channel", 6) * layout.um

        insts = sorted(layout.iterInstances(),
                       key=lambda i: getattr(i, "instanceName", ""))

        def pick(patterns):
            out = []
            for pat in patterns:
                for i in insts:
                    nm = getattr(i, "instanceName", "")
                    if re.fullmatch(pat, nm) and i not in out:
                        out.append(i)
            return out

        groups, stacks, fills = {}, {}, set()
        for e in spec.get("subcells", []):
            gname = e.get("group", "main")
            if gname not in groups:
                groups[gname] = layout.makeCellGroup(gname)
            members = pick(e.get("order", [e.get("match", ".*")]))
            if not members:
                log.warning(f"{e['name']}: no instances matched; skipped")
                continue
            st = groups[gname].addStack(e["name"], members,
                                        preserveOrder=True)
            stacks[e["name"]] = st
            if e.get("fill", True):
                fills.add(gname)

        for st in stacks.values():
            st.stack()
        #- fill the groups that want it, then taps: a tap goes around
        #- the finished column, dummies included
        for gname in fills:
            groups[gname].fillDummyTransistors()
        for st in stacks.values():
            st.addTaps()

        #- rows: abut left to right (bottoms aligned), rows bottom up
        rows = spec.get("rows", [])
        row_stacks = [[stacks[n] for n in row if n in stacks]
                      for row in rows]
        for row in row_stacks:
            for a, b in zip(row[1:], row[:-1]):
                a.abutRight(b)
        for g in groups.values():
            g.updateBoundingRect()
        for below, above in zip(row_stacks[:-1], row_stacks[1:]):
            top = max(int(s.y2) for s in below)
            dy = top + channel - min(int(s.y1) for s in above)
            for s in above:
                s.translate(0, dy)
        for g in groups.values():
            g.updateBoundingRect()
        for gname in fills:
            groups[gname].routeDummyDevices()

        #- the channel between the rows, and one per column, by name
        if len(row_stacks) >= 2:
            layout.addRoutingChannel(
                "mid",
                max(int(s.y2) for s in row_stacks[0]),
                min(int(s.y1) for s in row_stacks[1]))
        for e in spec.get("subcells", []):
            st = stacks.get(e["name"])
            if st is not None:
                layout.addRoutingChannel(e.get("channel", e["name"]),
                                         int(st.x1), int(st.x2),
                                         horizontal=False)

    def beforeRoute(self, layout):
        for s in self.spec.get("supplies", []):
            net = s["net"]
            if s.get("ring"):
                layout.addRouteRing("M1", net, s["ring"],
                                    widthmult=3, spacemult=2)
            layout.addPowerGuardConnection(
                net, excludeInstances=s.get("guard_exclude", ""))
            if s.get("strap"):
                layout.addPowerStrap(
                    net, "", s["strap"], terminals=("B",),
                    excludeInstances=s.get("strap_exclude", ""))
        from cicpy.core.mazerouter import route_stack_level
        routed, blocked = route_stack_level(layout, log=layout.log,
                                            only=None, boundary=True)
        layout.log.info(f"stack level: {len(routed)} routed, "
                        f"{len(blocked)} blocked")

    def afterPaint(self, layout):
        from cicpy.core.subcell import write_stack_cells
        write_stack_cells(layout, log=layout.log)


class AssemblyPycell:
    """The hierarchical top from the same sidecar.

    Places the published subcells at their published offsets (rows
    reused from the flat declaration), opens the assembly channel,
    registers the channels by the declared names, and routes every
    crossing net from the `hier: routes:` table -- a ChannelRoute
    per net with addRouteConnection drops -- plus the supply rings
    with addPowerConnection. The scaffold cell <CELL>_HIER finds
    this when <CELL>.yaml carries a `hier:` stanza and no
    <CELL>_HIER.py exists.
    """

    def __init__(self, spec):
        self.spec = spec

    def beforePlace(self, layout):
        layout.noPowerRoute = True
        layout.place_xspace = [0]
        layout.place_yspace = [0]
        layout.place_groupbreak = [len(self.spec.get("rows", [[]])[0])]

    def afterPlace(self, layout):
        hier = self.spec.get("hier", {})
        channel = hier.get("channel", 8) * layout.um
        rows = [["x" + n for n in row] for row in self.spec.get("rows", [])]

        #- Within a row the cells keep their PUBLISHED relative
        #- offsets: they overlap-tile, and the published coordinates
        #- are the arrangement DRC has already accepted. The painted
        #- reference needs xcell = -origin, the ports already land.
        y = 0
        row_tops = []
        for row in rows:
            anchor_x, tallest = None, 0
            for nm in row:
                inst = layout.getInstanceFromInstanceName(nm)
                if inst is None:
                    continue
                sub = inst.layoutcell
                if anchor_x is None:
                    anchor_x = int(sub.x1)
                inst.moveTo(int(sub.x1) - anchor_x, y)
                inst.xcell = -int(sub.x1)
                inst.ycell = -int(sub.y1)
                tallest = max(tallest, int(inst.height()))
            row_tops.append(y + tallest)
            y += tallest + channel
        layout.updateBoundingRect()

        if len(rows) >= 2:
            top_inst = layout.getInstanceFromInstanceName(rows[1][0])
            layout.addRoutingChannel("mid", row_tops[0], int(top_inst.y1))
        for e in self.spec.get("subcells", []):
            inst = layout.getInstanceFromInstanceName("x" + e["name"])
            if inst is not None and e.get("channel"):
                layout.addRoutingChannel(e["channel"], int(inst.x1),
                                         int(inst.x2), horizontal=False)

    def beforeRoute(self, layout):
        hier = self.spec.get("hier", {})
        for r in hier.get("routes", []):
            net = r["net"]
            layout.addChannelRoute(r.get("bar_layer", "M3"), net,
                                   r.get("channel", "mid"),
                                   r.get("track", 0))
            #- drops are DISCOVERED: every subcell instance exposing
            #- the net gets one, with the route's defaults; the
            #- `drops:` list only overrides -- layer, align, cuts,
            #- pin_cut -- for the instances that need it.
            defaults = {"layer": r.get("layer", "M2"),
                        "align": r.get("align", "center"),
                        "cuts": r.get("cuts", 2),
                        "pin_cut": r.get("pin_cut", True)}
            overrides = {}
            for d in r.get("drops", []):
                if isinstance(d, dict):
                    overrides[d["inst"]] = d
                else:
                    o = {"inst": d[0]}
                    if len(d) > 1: o["layer"] = d[1]
                    if len(d) > 2: o["align"] = d[2]
                    if "nopin" in d[3:]: o["pin_cut"] = False
                    overrides[d[0]] = o
            for inst in layout.iterInstances():
                nm = getattr(inst, "instanceName", "")
                if net not in getattr(inst, "instancePorts", {}):
                    continue
                o = dict(defaults)
                o.update(overrides.get(nm.lstrip("x"), {}))
                layout.addRouteConnection(net, f"^{re.escape(nm)}$", "t",
                                          o["layer"], align=o["align"],
                                          cuts=o["cuts"],
                                          pin_cut=o["pin_cut"])
            layout.trimChannelRoute(net)
        for sup in self.spec.get("supplies", []):
            side = sup.get("ring")
            if not side:
                continue
            layout.addRouteRing("M1", sup["net"], side,
                                widthmult=3, spacemult=2)
            layout.addPowerConnection(sup["net"], "",
                                      "top" if "t" in side else "bottom")
