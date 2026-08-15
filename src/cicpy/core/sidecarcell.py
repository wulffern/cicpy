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

    def _placeStacks(self, layout):
        """The device columns: built, filled, tapped, abutted.

        Called from afterPlace, which is also where the design's own
        subcell classes get theirs -- one method, in the order the
        recipe needs: the columns exist before a hook can adjust them.
        """
        spec = self.spec
        #- A CELL THAT HOLDS NO STACKS HAS NOTHING HERE. Its pieces
        #- are cells and placeHier tiled them; this is the step that
        #- builds device columns, and it is empty rather than skipped
        #- so the interface stays the same for both.
        if not spec.get("stacks"):
            return
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
        for e in spec.get("stacks", []):
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
        #- Both spellings of the index, because a schematic may draw the
        #- fills one per symbol (xfill_p_su_0 .. _10) or as one vector
        #- instance (xfill_p_su[10:0], netlisted as xfill_p_su<0>..<10>).
        #- The second is worth supporting: fills are the bulk of what is
        #- on the page -- 19 devices and their 76 supply pins out of 137
        #- placements in LELOTEMP_BIAS_IBP -- and a vector instance
        #- collapses each run to one symbol. Reading only the underscore
        #- form silently yields no counts for the vector form, and the
        #- column then builds with no fills at all rather than failing.
        counts = {}
        for inst in (getattr(getattr(layout, "ckt", None),
                             "instances", None) or []):
            name = getattr(inst, "name", "")
            m = (re.fullmatch(r"xfill_(.+)_(\d+)", name)
                 or re.fullmatch(r"xfill_(.+)<(\d+)>", name))
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
                  for e in spec.get("stacks", [])}
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
        for e in spec.get("stacks", []):
            st = stacks.get(e["name"])
            if st is not None:
                layout.addRoutingChannel(e.get("channel", e["name"]),
                                         int(st.x1), int(st.x2),
                                         horizontal=False)

    #- ------------------------------------------------------------
    #- the crossing nets, DECLARED
    #- ------------------------------------------------------------

    @staticmethod
    def declaredPort(layout, instanceName, port):
        """A placed block's published pin, by instance and port name."""
        inst = layout.getInstanceFromInstanceName(instanceName)
        if inst is None:
            return None
        rs = [c.get() for c in (getattr(inst, "children", []) or [])
              if getattr(c, "isPort", lambda: False)()
              and getattr(c, "name", "") == port]
        rs = [r for r in rs if r is not None]
        return rs[0] if rs else None

    def routePaths(self, layout):
        """Lay every path this cell DECLARES, in the order declared.

        A story told through `p.movex(p.track(...))` is a method call
        on a path that does not exist until something builds it, so it
        could only live inside a hook -- and the crossing nets of a top
        cell were four hundred lines of `beforeRoute` sitting beside a
        placement that was pure declaration. The steps are the same;
        what changes is that they are now DATA on the class, next to
        the `rows` they depend on, and they round-trip into the .cic
        through the anchors' own toJson.

        An entry is a dict:

            net      the net, and the name the router uses
            start    (instanceName, port) the path leaves
            stop     (instanceName, port) it lands on
            layer    the routing layer; the start pin's own by default
            at       which edge of the start rect to leave from
            options  cut options, "1cuts,2vcuts" by default
            steps    [(stepName, *args)], applied in order

        TWO SCOPES, because a cell has two kinds of net. A crossing net
        between two BLOCKS names its two ends -- `start`/`stop`, one
        published pin each -- and the story runs from one to the other.
        A net INSIDE a column has no two ends: it is a rail over every
        pin of that net in the column, which is what `||` means and
        what the search draws. Naming two of N pins to stand for the
        rail makes the declaration depend on which two, so an entry
        that omits `start`/`stop` is COLLECTED instead: every pin of
        the net in scope, through the same collector
        `addConnectivityRoute` uses. Add a device to the column and the
        rail grows over it with nothing in the file changing.

            net      the net, and the name the router uses
            layer    required when the pins are collected; there is no
                     start pin to take it from
            pins     an instance-name regex narrowing the collection
                     (default: every instance of the cell)

        `paths_only` names the nets to draw and skips the rest -- the
        gate a bisect needs, in one place rather than in each story.
        """
        for e, only in self.pathEntries():
            net = e["net"]
            if only is not None and net not in only:
                continue
            if e.get("start") or e.get("stop"):
                a = self.declaredPort(layout, *e["start"])
                b = self.declaredPort(layout, *e["stop"])
                if a is None or b is None:
                    missing = e["start"] if a is None else e["stop"]
                    layout.log.error(
                        f"paths: {net} has no pin at "
                        f"{missing[0]}.{missing[1]}")
                    continue
                p = layout.path(net, e.get("layer") or a.layer,
                                start=[a], stop=[b],
                                options=e.get("options", "1cuts,2vcuts"))
                p.start(at=e.get("at"))
            else:
                layer = e.get("layer")
                if not layer:
                    layout.log.error(
                        f"paths: {net} collects its pins and so must "
                        f"name a layer; there is no start pin to take "
                        f"one from")
                    continue
                p = layout.path(net, layer,
                                options=e.get("options", "1cuts,2vcuts"),
                                includeInstances=e.get("pins", ""),
                                excludeInstances=e.get("not_pins", ""))
                if not p.stopRects:
                    layout.log.error(
                        f"paths: {net} has no pin on {layer} in "
                        f"{e.get('pins') or 'this cell'}")
                    continue
            for st in e.get("steps", []):
                name, args = st[0], tuple(st[1:])
                fn = getattr(p, name, None)
                if not callable(fn):
                    layout.log.error(f"paths: {net} names no step {name!r}")
                    continue
                fn(*args)

    def pathEntries(self):
        """Every declared path with the `paths_only` that gates it.

        The cell's own, and then its columns'. A column is built as a
        cell of its own, so its class's declarations arrive here as the
        one entry in `spec["stacks"]` -- the same list the flat recipe
        reads for `order` and `wires`. One walk serves both, which is
        why a cell that places its own devices and one assembled from
        columns declare routing the same way.
        """
        out = [(e, getattr(self, "paths_only", None))
               for e in (getattr(self, "paths", None) or [])]
        for s in self.spec.get("stacks", []) or []:
            only = s.get("paths_only")
            for e in s.get("paths", []) or []:
                out.append((e, only))
        return out

    def mazeEntries(self):
        """Every declared maze search, the same way."""
        out = [(e, getattr(self, "paths_only", None))
               for e in (getattr(self, "mazes", None) or [])]
        for s in self.spec.get("stacks", []) or []:
            only = s.get("paths_only")
            for e in s.get("mazes", []) or []:
                out.append((e, only))
        return out

    def routeMazes(self, layout):
        """The searched nets, declared the same way.

        A maze route is not a Path and cannot become one -- it is a
        SEARCH, and what it takes is a budget of layers and two rects
        rather than a story. It is declared beside the paths so that
        `paths_only` gates both and a cell's crossing nets are all in
        one place:

            net, layers, between = [(inst, port), (inst, port)]
        """
        for e, only in self.mazeEntries():
            net = e["net"]
            if only is not None and net not in only:
                continue
            rects = [self.declaredPort(layout, *r) for r in e["between"]]
            if any(r is None for r in rects):
                layout.log.error(f"mazes: {net} is not on both blocks")
                continue
            layout.addMazeRoute(f"^{net}$", layers=list(e["layers"]),
                                rects=rects)

    def beforeRoute(self, layout):
        """The supplies, and the stack-level router.

        ONE METHOD FOR BOTH KINDS OF CELL. The ring is the same
        declaration either way; what differs is what it is attached
        TO, and that is not a flag but what the cell holds -- guard
        and tap geometry if it holds devices, the children's own
        published supply rects if it holds cells. The assembly recipe
        used to carry its own copy of this loop, so the two drifted:
        one grew `guard_exclude` and the other did not.
        """
        #- BEFORE the supplies, which is where the hand-written
        #- crossing-net hook used to run: a declared path lands on a
        #- block's published pin, and the rings are attached after.
        self.routePaths(layout)
        self.routeMazes(layout)
        devices = bool(self.spec.get("stacks"))
        for s in self.spec.get("supplies", []):
            net = s["net"]
            side = s.get("ring")
            if side:
                layout.addRouteRing("M1", net, side,
                                    widthmult=3, spacemult=2)
            if devices:
                layout.addPowerGuardConnection(
                    net, excludeInstances=s.get("guard_exclude", ""))
                if s.get("strap"):
                    layout.addPowerStrap(
                        net, "", s["strap"], terminals=("B",),
                        excludeInstances=s.get("strap_exclude", ""))
            elif side:
                #- addPowerStrap, NOT addPowerConnection. The one this
                #- replaces copies each published supply RECT and
                #- stretches it to the ring on that rect's own layer,
                #- so a child's supply pin drags its layer across
                #- everything between it and the ring. On a library
                #- whose pins overhang their abutment box that shorts
                #- the block: measured on a REY_ATR cell, on the bare
                #- placement with no signal route anywhere, every
                #- signal in the cell was already tied to VDD or VSS.
                #- addPowerStrap carries the same net to the same ring
                #- one ROUTING width wide instead of one pin wide, on
                #- the ring's layer, with the via down on the pin.
                #-
                #- `pin_strap: true` on the supply entry restores the
                #- old call for a design that depends on its geometry.
                #- MEASURED, and it is why this is opt-in rather than
                #- swapped: addPowerStrap is NOT a drop-in here. An
                #- assembly has no device terminals to strap, and
                #- substituting it on LELOTEMP_BIAS_IBP produced a real
                #- LPI,VCP,VDD_1V8 component of 242 rects -- a supply
                #- short where there had been none. So the default is
                #- to draw NOTHING and say so: an open is visible in
                #- every check, a supply short is invisible to DRC.
                where = s.get("strap") or ("top" if "t" in side else "bottom")
                if s.get("pin_strap"):
                    layout.addPowerConnection(net, "", where)
                else:
                    layout.log.warning(
                        f"supplies: {net} has a ring but no connection to "
                        f"it. addPowerConnection is opt-in -- it copies "
                        f"each published supply rect and stretches it to "
                        f"the ring on that rect's own layer, which shorts "
                        f"a block whose pins overhang. Say "
                        f"'pin_strap': True on this supply entry to keep "
                        f"it, or connect {net} in the cell's own "
                        f"beforeRoute.")
        if not devices:
            return
        from cicpy.core.mazerouter import route_stack_level
        routed, blocked = route_stack_level(layout, log=layout.log,
                                            only=None, boundary=True)
        layout.log.info(f"stack level: {len(routed)} routed, "
                        f"{len(blocked)} blocked")

    #- ------------------------------------------------------------
    #- Publication, and the design's own phases
    #-
    #- These were SubcellLayout's, which was this same recipe plus a
    #- constructor -- "one subcell built as a cell of its own", which
    #- is what EVERY cell is now. A cell built as a piece of a parent
    #- carries `entry` (its plan) and `parent_name`; a top-level one
    #- carries neither, and every method below reads what it finds.
    #- ------------------------------------------------------------

    entry = None
    parent_name = ""

    def afterPorts(self, layout):
        """Put the supply ports where a parent's ring can reach them.

        FOR A CELL BUILT AS A PIECE, which is what `entry` says. A
        top-level cell's ports are its children's own published rects,
        already where those cells decided; moving them here instead
        picked whatever the node graph listed first and published
        three of one cell's pins as one net (measured on
        LELOTEMP_BIAS_IBP: VD1 claiming LPO and PWRUP_1V8).

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
        if self.entry is None:
            for g in self.groups(layout):
                g.afterPorts({})
            return
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
            #- AS WIDE AS THE GUARD. The bulk columns straddle the
            #- cell edge -- every one of them is 9600 wide against a
            #- box that cuts at 4800 -- so clipping in x published half
            #- a guard: one 0.48 um place for the parent to land on,
            #- for the net it has to reach everywhere. The guard is
            #- what the supply IS in this library, and the half outside
            #- the box is not spare, it is the half the abutted
            #- neighbour shares.
            #-
            #- Still clipped in Y, which is what the original guard was
            #- against: a port running past the top or bottom of the
            #- column inflates the box and moves the origin every
            #- parent track was tuned to. X does not, because the
            #- column's own guard is already there.
            pr = pr.getCopy()
            pr.y1 = max(pr.y1, box.y1)
            pr.y2 = min(pr.y2, box.y2)
            layout.updatePort(net, pr)
        for g in self.groups(layout):
            g.afterPorts(self.entry or {})

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

    #- ---------------------------------------------------------------
    #- The design's own phases. Ordinary polymorphism: a declared
    #- subcell subclasses the real StackGroup and the base declares
    #- every phase as a no-op, so calling the method IS the dispatch.
    #- beforePlace and beforeRoute keep their own path through
    #- run_stack_pycells, where beforeRoute's answer decides whether
    #- the built-in router leaves the stack alone.
    #- ---------------------------------------------------------------

    def groups(self, layout):
        from .subcell import subcell_groups
        return list((subcell_groups(layout) or {}).values())

    def afterPlace(self, layout):
        self._placeStacks(layout)
        for g in self.groups(layout):
            g.afterPlace(self.entry or {})

    def afterRoute(self, layout):
        for g in self.groups(layout):
            g.afterRoute(self.entry or {})

    def beforePaint(self, layout):
        for g in self.groups(layout):
            g.beforePaint(self.entry or {})

    def afterPaint(self, layout):
        for g in self.groups(layout):
            g.afterPaint(self.entry or {})

    def beforePorts(self, layout):
        for g in self.groups(layout):
            g.beforePorts(self.entry or {})

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

    Mixed into SidecarCell. A cell gets this recipe by HOLDING
    subcells -- see SidecarCell.place()/route(), which branch on
    `self.subcells`, and hierarchy(), which is unconditional. It is
    not `routes` that decides: an assembled cell may declare
    `routes = []` and lay its crossing nets some other way. A design
    that needs more than the declarations overrides place()/route()
    on its own class and calls super().
    """

    #- ------------------------------------------------------------
    #- hierarchy: the subcells, built before the parent is placed
    #- ------------------------------------------------------------

    def hierarchy(self):
        """Every declared piece, built as a cell.

        UNCONDITIONAL. It used to run only for a cell that declared
        `routes`, so what a cell was MADE OF depended on whether its
        crossing nets happened to be written down -- two different
        builds of the same declaration, and the one cell in this
        design that had no routes to declare stayed a flat cell with
        150 lines of Rect and Cut reaching into its neighbours'
        instances. A declared piece is a cell; `routes` only says how
        the pieces are joined.

        The split and the definition of the built cells belong to the
        design (`Design.buildSubcells`) -- a cell per part, registered
        ahead of this one so the parent builds against the children
        built this run rather than last run's files. What a part
        BECOMES is here, because that is the recipe's business.
        """
        specs = [{"name": e["name"], "match": e.get("match", ""),
                  "type": e.get("type", "stack")}
                 for e in self.spec.get("subcells", [])]
        #- the router's paste-ready blocks belong in THIS cell's file,
        #- where the subcell classes are; cleared here so one run's
        #- blocks accumulate and the last run's do not survive it
        try:
            os.remove(os.path.join(getattr(self, "dirname", "") or "",
                                   self.name + ".routes.py"))
        except OSError:
            pass
        dirs = {}

        def build(entry, ckt):
            entry["port_dirs"] = dirs.get(entry["stack"], {})
            return self._buildSubcell(entry, ckt)

        #- the directions need the whole plan, and the plan comes back
        #- from the split -- so the first pass through is a dry one
        from .hierarchy import plan_from_netlist
        plan = plan_from_netlist(self.ckt, [s for s in specs
                                            if s.get("match")], self.name)
        if not plan:
            if specs:
                self.log.warning(f"{self.name}: declares subcells but "
                                 f"the split found none")
            return
        dirs = self._portDirections(plan)

        built = self.parent.buildSubcells(self, specs, build)
        #- what this run built, for the step that writes their views
        self.subcells_built = [e["name"] for e in built]

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
            #- A STACK, NOT A SUBCELL. The two used to be one key and
            #- the ambiguity was the whole knot: a child built from
            #- `subcells: [itself]` declares that it is assembled from
            #- a copy of itself, so the recipe could not be run
            #- unconditionally without recursing forever. A cell is
            #- assembled from `subcells` -- other cells -- and places
            #- devices into `stacks`. A child has stacks and no
            #- subcells, which is what ends the recursion.
            "stacks": [e],
            "rows": [[e["name"]]],
            "supplies": [{k: v for k, v in s.items() if k != "ring"}
                         for s in spec.get("supplies", [])],
        }

    def _buildSubcell(self, entry, ckt):
        name = entry["name"]
        design = self.parent
        #- AN ORDINARY SIDECAR CELL, from a spec rather than from a
        #- class. There is no separate kind of object for a piece:
        #- what made one look special -- its spec is derived, its
        #- ports face its parent -- is data, not type.
        from cicpy.sidecar import SidecarCell
        cell = SidecarCell(spec=self._subcellSpec(entry))
        cell.entry = entry
        cell.parent_name = self.name
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
        #- THE SUPPLIES ARE beforeRoute's, for both kinds of cell.
        #- They were here as well, which meant an assembly laid its
        #- rings from a second copy of the same loop.
        LayoutCell.route(self)
        #- AND THE CONTACTS MEET THE CELLS BELOW. A parent and a child
        #- contacting the same port each centre on their own copy of
        #- it -- the child on the pin, the parent on the port rect the
        #- child clipped to its column -- and magic cannot represent
        #- two contacts of one type that partially overlap across a
        #- cell boundary. Measured: LELOTEMP_BIAS_IBP is 0 DRC with
        #- this and 4 without, LELOTEMP_CCMP 0 either way.
        self._alignCutsToSubcellCuts()
