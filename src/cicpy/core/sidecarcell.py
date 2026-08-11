"""Placement from the sidecar alone.

The <CELL>.py sidecar (see cicpy/sidecar.py) declares WHAT the
subcells are; with `order` per subcell and `rows` for the floorplan
it declares the whole placement, and this module is the recipe that
executes the compiled spec:

    stacks (in declared member order) -> taps and dummy fill ->
    rows abutted left to right, stacked bottom to top -> a routing
    channel between the rows and one per column -> supply rings and
    guard connections -> the stack-level router -> publish.

A classic <CELL>.py pycell -- module-level hooks and `data`, no
Subcell classes -- still works exactly as before, for the cell that
needs something the recipe cannot say.

Spec shape (all placement keys optional; their presence enables
this; cicpy/sidecar.py compiles the module into exactly this dict):

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
import os
import re
import logging

from .layoutcell import LayoutCell

log = logging.getLogger("SidecarPycell")


class SidecarPycell:
    """The FLAT recipe: the devices placed, routed.

    Hooks only -- `self.spec` is the compiled sidecar and the cell is
    `layout`, which for a SidecarCell is the same object (see
    cicpy/sidecar.py). Mixed into SidecarCell rather than handed over
    as a module, so a design overrides a step and calls super().
    """

    @staticmethod
    def recipe_data():
        """The data-driven half of the recipe, in pycell `data` form."""
        return {"afterPaint": [{"resetOrigins": [[1]]}]}

    # -- hooks -------------------------------------------------------

    def beforePlace(self, layout):
        #- publication (subcell_spec) reads the spec off the layout:
        #- one truth, already compiled from the sidecar class
        layout._sidecar_spec = self.spec
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
            #- the DECLARED class is the group that gets built, so
            #- its hooks run with self = the placed group
            st = groups[gname].addStack(e["name"], members,
                                        preserveOrder=True,
                                        cls=e.get("cls"))
            stacks[e["name"]] = st
            if e.get("fill", True):
                fills.add(gname)


        for st in stacks.values():
            st.stack()
        #- fill the groups that want it, then taps: a tap goes around
        #- the finished column, dummies included
        #-
        #- HOW MANY fills each column wants comes from the NETLIST.
        #- The schematic names them (xfill_<stack>_<n>) because it
        #- records the devices the layout has, and height matching --
        #- the rule that invented them -- has nothing to match against
        #- once a column is built as a cell of its own. Netlist first,
        #- height matching for the column the netlist says nothing of.
        counts = {}
        for inst in (getattr(getattr(layout, "ckt", None),
                             "instances", None) or []):
            m = re.fullmatch(r"xfill_(.+)_(\d+)", getattr(inst, "name", ""))
            if m:
                counts[m.group(1)] = max(counts.get(m.group(1), 0),
                                         int(m.group(2)) + 1)
        for gname in fills:
            #- BOTTOM, not top. A dummy is a supply device now -- its
            #- bars ride VDD/VSS -- and every rail in a column spans
            #- upward over the real pins: a supply bar inside that span
            #- blocks the lane (measured: the drain lane fell to an M2
            #- rail whose pads then blocked the gate tabs). Below the
            #- lowest pin it is outside every span.
            groups[gname].fillDummyTransistors(direction="bottom",
                                               counts=counts)
        for st in stacks.values():
            st.addTaps()

        #- rows: abut left to right (bottoms aligned), rows bottom up.
        #- A subcell's `xspace` (um) opens a gap on ITS LEFT: the seam
        #- rule between two cells is a property of the pair, and abut
        #- is only right when their edge geometry says so (a pnp
        #- array's guard against an nmos stack is not such a pair --
        #- magic refuses the li abutment, measured).
        xspace = {e["name"]: e.get("xspace", 0)
                  for e in spec.get("subcells", [])}
        rows = spec.get("rows", [])
        row_stacks = [[stacks[n] for n in row if n in stacks]
                      for row in rows]
        row_names = [[n for n in row if n in stacks] for row in rows]
        for row, names in zip(row_stacks, row_names):
            for (a, b), nm in zip(zip(row[1:], row[:-1]), names[1:]):
                a.abutRight(b)
                gap = xspace.get(nm, 0)
                if gap:
                    a.translate(int(gap * layout.um), 0)
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


class HierPycell:
    """The ASSEMBLY recipe: a cell made of cells, in one pass.

    `hierarchy()` is the whole of the new part. It splits the cell's
    own netlist by the sidecar's membership regexes, builds a
    LayoutCell per subcell from its own Subckt -- placed from its own
    origin, routed and registered in the design -- and leaves the
    parent holding one instance of each. place() then tiles those
    instances row by row from the same `rows` declaration the flat
    recipe uses, and route() lays every crossing net from the
    `hier: routes:` table -- a ChannelRoute per net with
    addRouteConnection drops -- plus the supply rings, before handing
    over to the ordinary router.

    Mixed into SidecarCell. A cell gets this recipe by DECLARING
    `routes`; a design that needs more than the declarations
    overrides place()/route() on its own class and calls super().
    """

    #- ------------------------------------------------------------
    #- hierarchy: the subcells, built before the parent is placed
    #- ------------------------------------------------------------

    def hierarchy(self):
        """Split the netlist and build a cell per subcell.

        In memory and in one process: nothing is written to disk and
        re-parsed, because nothing here needs geometry. Membership
        and boundary nets are properties of the NETLIST (see
        core/hierarchy.py), so each part can be built as a cell in
        its own right and the parent instantiates it -- which is what
        the two-pass build, a generated <CELL>_HIER.spice and a
        second process between them used to buy.

        Ordering is the one subtlety: a subcell is registered in
        design.cells BEFORE the parent places anything, and
        MagicDesign.getLayoutCell prefers design.cells over the .mag
        library, so the parent builds against the children built this
        run rather than last run's files.
        """
        spec = self.spec
        if "hier" not in spec:
            return
        from .hierarchy import plan_from_netlist, split_subckt

        specs = [{"name": e["name"], "match": e.get("match", ""),
                  "type": e.get("type", "stack")}
                 for e in spec.get("subcells", []) if e.get("match")]
        plan = plan_from_netlist(self.ckt, specs, self.name)
        if not plan:
            self.log.warning(f"{self.name}: declares an assembly but "
                             f"the split found no subcells")
            return
        made = split_subckt(self.ckt, plan)
        #- the router's paste-ready blocks belong in THIS cell's file,
        #- where the subcell classes are; cleared here so one run's
        #- blocks accumulate and the last run's do not survive it
        try:
            os.remove(os.path.join(getattr(self, "dirname", "") or "",
                                   self.name + ".routes.py"))
        except OSError:
            pass
        dirs = self._portDirections(plan)
        for entry in plan:
            entry["port_dirs"] = dirs.get(entry["stack"], {})
            self._buildSubcell(entry, made[entry["stack"]])
        #- what this run built, for the step that writes their views
        self.subcells_built = [e["name"] for e in plan]

    def _portDirections(self, plan):
        """{subcell: {net: (dx, dy)}} -- which way each port faces.

        A port is the one thing the parent routes to, so it should
        face the traffic: the pin at the end of the column the net
        LEAVES by. Which end that is is a floorplan question, and the
        floorplan is declared -- `rows` says which subcells sit above,
        below and beside this one, so the net's other owners give a
        direction without any geometry existing yet.

        This is the rule the copy-out publication computed from the
        placed layout, as the centroid of the net's pins OUTSIDE the
        subcell. Read off the rows instead, it is available before
        anything is placed, which is what lets the subcell be built
        rather than copied. A net with no other owner -- the parent's
        own IO, living wholly in one column -- gets no direction and
        keeps whatever pin it lands on.
        """
        where = {}
        for r, row in enumerate(self.spec.get("rows", []) or []):
            for c, nm in enumerate(row):
                where[nm] = (c, r)
        owners = {}
        for e in plan:
            for net in e["ports"]:
                owners.setdefault(net, []).append(e["stack"])
        out = {}
        for e in plan:
            me = where.get(e["stack"])
            if me is None:
                continue
            mine = {}
            for net in e["ports"]:
                others = [where[o] for o in owners.get(net, [])
                          if o != e["stack"] and o in where]
                if not others:
                    continue
                dx = sum(o[0] for o in others) / len(others) - me[0]
                dy = sum(o[1] for o in others) / len(others) - me[1]
                #- ACROSS the rows beats along one: the columns are
                #- tall and thin, so a row hop is the long journey and
                #- the end of the column is what shortens it
                if dy:
                    mine[net] = (0, 1 if dy > 0 else -1)
                elif dx:
                    mine[net] = (1 if dx > 0 else -1, 0)
            out[e["stack"]] = mine
        return out

    def _subcellSpec(self, entry):
        """The sidecar spec of ONE subcell, as a cell of its own.

        The same recipe the flat build runs, narrowed to a single
        subcell in a single row -- so a subcell is placed, filled,
        tapped and routed exactly as it was as a region of the flat
        parent, and its `wires` block still applies.

        The supply RING is dropped and everything else kept: a ring
        belongs to the cell that owns the boundary, which is the
        parent. The guard connections and the straps are inside the
        column and belong to the subcell.
        """
        spec = self.spec
        e = next(x for x in spec.get("subcells", [])
                 if x["name"] == entry["stack"])
        return {
            "place": dict(spec.get("place", {})),
            "subcells": [e],
            "rows": [[e["name"]]],
            "supplies": [{k: v for k, v in s.items() if k != "ring"}
                         for s in spec.get("supplies", [])],
        }

    def _buildSubcell(self, entry, ckt):
        name = entry["name"]
        design = self.parent
        cell = SubcellLayout(self._subcellSpec(entry), entry,
                             parent_name=self.name)
        cell.name = name
        cell.ckt = ckt
        cell.subckt = ckt
        cell.parent = design
        cell.design = getattr(self, "design", None) or design
        cell.dirname = getattr(self, "dirname", "")
        cell.strict_route = getattr(self, "strict_route", False)
        cell.libpath = getattr(self, "libpath", "")
        cell.routes_owner = self.name
        self.log.info(f"{self.name}: building {name} "
                      f"({len(entry['instances'])} instances, "
                      f"{len(entry['ports'])} ports)")
        cell.layout(cell, cell.data)

        self._setAbutmentBox(cell)

        #- the netlist the SCHEMATIC side compares against, amended
        #- with the fill devices placement invented. They cannot
        #- change the port set -- every fill terminal rides the
        #- subcell's own supply, which is already a port -- and that
        #- is asserted rather than assumed.
        self._amendSubcellNetlist(cell, entry)

        design.cells[name] = cell
        if name in getattr(design, "cellnames", []):
            design.cellnames.remove(name)
        #- ahead of the parent: defined before it is used
        design.cellnames.insert(0, name)
        return cell

    @staticmethod
    def columnBox(cell):
        """The cell's COLUMN: its single built stack, else the cell.

        The box a parent abuts, and the box a port is clipped to --
        one definition, because they are the same box.
        """
        groups = getattr(cell, "cellgroups", None) or []
        stacks = [s for g in groups for s in (getattr(g, "stacks", []) or [])]
        if len(stacks) == 1:
            return stacks[0]
        cell.setBoundaryIgnoreRouting(True)
        cell.updateBoundingRect()
        return cell

    def _setAbutmentBox(self, cell):
        """The box a parent tiles this subcell by: its COLUMN.

        Not the extent of its geometry. A column carries its guard
        ring past its own column box so that two abutted columns MERGE
        their guards -- and its trunk rails can stand a lane outside
        it too. Tiled by the geometry, every seam opens by whatever
        happened to stick out and the guards stop merging; tiled by
        the column, the arrangement is the flat build's, which is the
        one DRC has already accepted.

        This IS the box the flat recipe abutted: `abutRight` works on
        the built group. So the cell is translated to put that box at
        the origin -- which makes the model and the painted geometry
        agree, since an instance maps a child's origin to its own
        position -- and the box is then stated, not measured.
        """
        box = self.columnBox(cell)
        x1, y1 = int(box.x1), int(box.y1)
        w, h = int(box.x2) - x1, int(box.y2) - y1
        cell.translate(-x1, -y1)
        cell.x1, cell.y1, cell.x2, cell.y2 = 0, 0, w, h

    def _amendSubcellNetlist(self, cell, entry):
        from .subcell import stack_subckt
        placed = dict(entry)
        placed["instances"] = sorted(
            getattr(i, "instanceName", "") or ""
            for i in cell.iterInstances())
        lines, fp = stack_subckt(cell, placed)
        #- the grouping-drift guard: instance names decide placement
        #- groups, so a rename silently moves a device to another
        #- subcell and both sides would then agree, wrongly
        cell.cic_fingerprint = fp
        try:
            from cicspi import Subckt
            parser = getattr(getattr(self, "ckt", None), "parser", None)
            ckt = Subckt(parser)
            ckt.parse(list(lines), 0)
        except Exception as e:
            self.log.warning(f"{cell.name}: could not rebuild the "
                             f"netlist with its fills: {e}")
            return
        if sorted(ckt.nodes) != sorted(entry["ports"]):
            self.log.error(
                f"{cell.name}: the fills changed the port set "
                f"{sorted(entry['ports'])} -> {sorted(ckt.nodes)}; "
                f"the split was decided before they existed")
        cell.ckt = ckt
        cell.subckt = ckt

    #- ------------------------------------------------------------
    #- place: the floorplan, from the same rows the flat build uses
    #- ------------------------------------------------------------

    def placeHier(self):
        spec = self.spec
        hier = spec.get("hier", {})
        channel = hier.get("channel", 8) * self.um
        rows = [["x" + n for n in row] for row in spec.get("rows", [])]
        xspace = {"x" + e["name"]: e.get("xspace", 0)
                  for e in spec.get("subcells", [])}

        insts = {}
        for cktInst in self.ckt.orderInstancesByGroup():
            insts[cktInst.name] = cktInst

        #- THE FLOORPLAN FIRST, from the built boxes alone: within a
        #- row the columns ABUT, left to right, exactly as the flat
        #- recipe abuts the groups -- a subcell's box IS its column,
        #- and its guard ring overhangs into the neighbour's, which is
        #- how two abutted columns share one guard. `xspace` (um)
        #- opens a gap on a subcell's LEFT for the pair whose edge
        #- geometry refuses to abut.
        slots = {}
        y = 0
        row_tops = []
        for row in rows:
            x, tallest = 0, 0
            for nm in row:
                cktInst = insts.get(nm)
                if cktInst is None:
                    self.log.warning(f"place: {nm} declared in rows "
                                     f"but not in the netlist; skipped")
                    continue
                sub = self.parent.getLayoutCell(cktInst.subcktName)
                if sub is None:
                    raise ValueError(f"place: no built cell "
                                     f"{cktInst.subcktName} for {nm}")
                x += int(xspace.get(nm, 0) * self.um)
                slots[nm] = (x, y)
                x += int(sub.x2 - sub.x1)
                tallest = max(tallest, int(sub.y2 - sub.y1))
            row_tops.append(y + tallest)
            y += tallest + channel

        #- then place in NETLIST order -- everything downstream that
        #- iterates instances (drops, painting) sees that order, and
        #- the build stays deterministic against the flat one
        for cktInst in self.ckt.orderInstancesByGroup():
            s = slots.get(cktInst.name)
            if s is None:
                #- a netlist instance the rows do not claim still has
                #- to exist for LVS; stack the strays above, loudly
                self.log.warning(f"place: {cktInst.name} not in any "
                                 f"row; placed above the floorplan")
                inst = self.addInstance(cktInst, 0, y)
                y += int(inst.height()) + channel
                continue
            x, ry = s
            self.addInstance(cktInst, x, ry)

        self.updateBoundingRect()

        #- the channel between the rows, and one per column, by name
        if len(rows) >= 2 and rows[1] and rows[1][0] in slots:
            self.addRoutingChannel("mid", row_tops[0],
                                   slots[rows[1][0]][1])
        for e in spec.get("subcells", []):
            inst = self.getInstanceFromInstanceName("x" + e["name"])
            if inst is not None and e.get("channel"):
                self.addRoutingChannel(e["channel"], int(inst.x1),
                                       int(inst.x2), horizontal=False)

    def routeHier(self):
        hier = self.spec.get("hier", {})
        for r in hier.get("routes", []):
            net = r["net"]
            self.addChannelRoute(r.get("bar_layer", "M3"), net,
                                 r.get("channel", "mid"),
                                 r.get("track", 0))
            #- drops are DISCOVERED: every subcell instance exposing
            #- the net gets one, with the route's defaults; the
            #- `drops:` list only overrides -- layer, align, cuts,
            #- pin_cut -- for the instances that need it.
            defaults = {"layer": r.get("layer", "M2"),
                        "align": r.get("align", "center"),
                        "cuts": r.get("cuts", 2),
                        "pin_cut": r.get("pin_cut", True),
                        "cut_shape": r.get("cut_shape", "auto")}
            overrides = {}
            for d in r.get("drops", []):
                if isinstance(d, dict):
                    overrides[d["inst"]] = d
                else:
                    o = {"inst": d[0]}
                    if len(d) > 1: o["layer"] = d[1]
                    if len(d) > 2: o["align"] = d[2]
                    if "nopin" in d[3:]: o["pin_cut"] = False
                    if "cutv" in d[3:]: o["cut_shape"] = "v"
                    if "cuth" in d[3:]: o["cut_shape"] = "h"
                    overrides[d[0]] = o
            for inst in self.iterInstances():
                nm = getattr(inst, "instanceName", "")
                if net not in getattr(inst, "instancePorts", {}):
                    continue
                o = dict(defaults)
                o.update(overrides.get(nm.lstrip("x"), {}))
                #- {"inst": ..., "skip": True} suppresses a DISCOVERED
                #- drop: for the column whose pin the net reaches some
                #- other way (a seam hop), where the drop's vertical
                #- would run the length of the column and clip every
                #- other net's pin stack on the way (measured)
                if o.get("skip"):
                    continue
                self.addRailConnection(net, f"^{re.escape(nm)}$", "t",
                                        o["layer"], align=o["align"],
                                        cuts=o["cuts"],
                                        pin_cut=o["pin_cut"],
                                        cut_shape=o["cut_shape"])
            #- a route may keep an end at the cell edge as its PIN for
            #- the level above: "trim" names the ends to pull back
            #- (default both; "l"/"b" low end, "r"/"t" high end, "" none)
            trim_ends = r.get("trim", "lr")
            if trim_ends:
                self.trimChannelRoute(net, ends=trim_ends)
        for sup in self.spec.get("supplies", []):
            side = sup.get("ring")
            if not side:
                continue
            self.addRouteRing("M1", sup["net"], side,
                              widthmult=3, spacemult=2)
            self.addPowerConnection(sup["net"], "",
                                    "top" if "t" in side else "bottom")
        LayoutCell.route(self)


class SubcellLayout(SidecarPycell, LayoutCell):
    """One subcell, built as a cell of its own.

    The FLAT recipe over a one-subcell spec: the same placement, the
    same fill and taps, the same stack-level router, from the
    subcell's own Subckt and from its own origin. There is nothing
    special about it -- which is the point. A subcell used to be a
    COPY of a region of its parent's geometry, and everything that
    made that hard (the parent's absolute coordinates, the guard
    overhang window, deciding which rects belonged) was an artefact
    of copying rather than building.
    """

    def __init__(self, spec, entry, parent_name=""):
        LayoutCell.__init__(self)
        self.spec = spec
        self.entry = entry
        self.parent_name = parent_name
        self.noPowerRoute = True
        self.data = SidecarPycell.recipe_data()

    def afterPorts(self, layout):
        """Put the supply ports where a parent's ring can reach them.

        addAllPorts takes the FIRST rect it finds on the net, which
        for a supply is whichever source pin iteration order landed
        on -- somewhere up the column, behind every other net's pins.
        A parent then stretches its ring to that pin and the stretch
        crosses the column: measured, one M1 rect 4.5 um wide and 28
        um tall through the bias column, shorting VBP, VCP, VDS and
        VO into VDD_1V8 in one go.

        A supply port belongs on the BULK column -- the guard and tap
        geometry, which is continuous through the tap row and carries
        the supply by construction -- at the end of the cell the
        parent's ring is on: ground at the bottom, power at the top.
        The ring then reaches it through pure guard, and the pin
        layer over the devices stays free.
        """
        from .mazerouter import supply_nets, supply_polarity
        supplies = supply_nets(layout)
        dirs = (self.entry or {}).get("port_dirs", {}) or {}
        box = HierPycell.columnBox(layout)
        for net in list(getattr(layout, "ports", {}) or {}):
            if net not in supplies:
                #- a signal port faces the traffic: the pin at the end
                #- of the column the net leaves by (see
                #- HierPycell._portDirections). Left as addAllPorts
                #- found it -- the FIRST rect on the net -- a drop from
                #- the parent's channel lands on whichever pin
                #- iteration order reached and runs the length of the
                #- column to get there, through every other net's pin
                #- stack (measured: VD1 in n_load_a, two met1 spacing
                #- errors against VBP's drop).
                d = dirs.get(net)
                if d is None:
                    continue
                rects = self._pinRects(layout, net)
                if not rects:
                    continue
                key = {(0, 1): lambda r: r.y2, (0, -1): lambda r: -r.y1,
                       (1, 0): lambda r: r.x2, (-1, 0): lambda r: -r.x1}
                layout.updatePort(net, max(rects, key=key[tuple(d)]))
                continue
            g = layout.nodeGraph.get(net)
            if g is None:
                continue
            bulks, allpins = [], []
            for port in getattr(g, "ports", []):
                r = port.get() if hasattr(port, "get") else None
                if r is None:
                    continue
                allpins.append(r)
                if getattr(port, "childName", "") == "B":
                    bulks.append(r)
            cands = bulks or allpins
            if not cands:
                continue
            if supply_polarity(net) == "ground":
                pr = min(cands, key=lambda r: r.y1)
            else:
                pr = max(cands, key=lambda r: r.y2)
            #- clipped to the column: the bulk columns straddle the
            #- cell edge, and a port poking past the box inflates it,
            #- which moves the origin every parent track was tuned to
            pr = pr.getCopy()
            pr.x1 = max(pr.x1, box.x1)
            pr.x2 = min(pr.x2, box.x2)
            pr.y1 = max(pr.y1, box.y1)
            pr.y2 = min(pr.y2, box.y2)
            layout.updatePort(net, pr)

    @staticmethod
    def _pinRects(layout, net):
        """Every pin rect on this net, from the node graph."""
        g = layout.nodeGraph.get(net)
        if g is None:
            return []
        out = []
        for port in getattr(g, "ports", []):
            r = port.get() if hasattr(port, "get") else None
            if r is not None:
                out.append(r)
        return out

    def _runStackPycells(self):
        """The subcell's own hooks, found under the name it is BUILT as.

        The plan a fresh walk would produce here names the one stack
        after this cell -- LELOTEMP_OTAR_P_BIAS_P_BIAS -- and the
        `<SUBCELLNAME>.py` escape hatch is looked up by that name. The
        parent's name is what makes it come out right.
        """
        from .subcell import run_stack_pycells
        try:
            run_stack_pycells(self, log=self.log,
                              parent_name=self.parent_name or None)
        except Exception as e:
            self.log.error(f"stack pycells: {e}")
