"""What the metal actually connects, judged against what the netlist says.

Two sides, and the check is the difference between them.

The NETLIST side is `LayoutCell.nodeGraph` -- cicpy's `Graph`, and
ciccreator's before it: one net name to the list of instance terminals
on it, built from the spice as the cell is placed. It is the INTENT, and
it is exactly one level deep. It knows this cell's own instances' pins
and nothing at all about what the metal inside them does.

The GEOMETRY side is `LayoutCell._collectPhysicalRects` flooded into
connected components: every touching rect on layers that connect, joined
regardless of what anyone calls it. It is the OBSERVATION.

Laying one on the other gives the two verdicts:

    SHORT   one component carries terminals of two nets
    OPEN    one net's terminals land in more than one component

This lived in `LayoutCell` and was most of a thousand lines of it, mixed
in with placement, routing and painting. It is its own concern: nothing
here changes the layout, and everything here is about judging one.
`LayoutCell` keeps thin methods that delegate, so `cell.checkConnectivity()`
still means what it always did.

Note what is NOT here. `_collectPhysicalRects` stays on `LayoutCell`,
because the track map, the blockers view and the maze router all read the
same list -- the flood is a consumer of it, not its owner. So do the
technology predicates (`_layersConnectForConnectivity` and friends),
which are properties of the layer rules.
"""
import re
import logging
from collections import defaultdict

from .cell import Cell


class Connectivity:
    """The connectivity check for one `LayoutCell`."""

    def __init__(self, cell):
        self.cell = cell
        self.log = getattr(cell, "log", None) or logging.getLogger("Connectivity")

    def _getRouteSource(self, rect):
        if hasattr(rect, "route_owner_info"):
            return rect.route_owner_info
        parent = getattr(rect, "parent", None)
        seen = set()
        while parent is not None and id(parent) not in seen:
            seen.add(id(parent))
            if hasattr(parent, "isRoute") and parent.isRoute():
                return {
                    "name": getattr(parent, "name", ""),
                    "net": getattr(parent, "net", ""),
                    "layer": getattr(parent, "routeLayer", ""),
                    "route": getattr(parent, "route_", ""),
                    "options": getattr(parent, "options", ""),
                    "debug_api": getattr(parent, "debug_api", ""),
                    "debug_callsite": getattr(parent, "debug_callsite", ""),
                    "debug_command": getattr(parent, "debug_command", ""),
                    "debug_internal": getattr(parent, "debug_internal", False),
                }
            parent = getattr(parent, "parent", None)
        return None

    @staticmethod
    def _getShapeOwner(rect):
        """Name the instance or cut a rect came out of.

        A bridge whose two rects have no `route` is geometry somebody
        PLACED, and without this the report says so only by omission --
        which reads as "unknown" and sends the reader looking at the
        router. Naming the instance turns four anonymous boxes into
        "these two devices touch".
        """
        parent = getattr(rect, "parent", None)
        seen = set()
        chain = []
        while parent is not None and id(parent) not in seen:
            seen.add(id(parent))
            if hasattr(parent, "isRoute") and parent.isRoute():
                return None
            iname = getattr(parent, "instanceName", "")
            cname = getattr(parent, "name", "")
            if iname and iname != cname:
                chain.append(f"{iname}:{cname}" if cname else iname)
            elif cname:
                chain.append(str(cname))
            parent = getattr(parent, "parent", None)
        if not chain:
            return None
        #- innermost first, and drop the top cell: it is on every line
        return " < ".join(chain[:3])

    def _collectNetAnchorRects(self, target_layer=""):
        anchors = []
        seen = set()
        for node in self.cell.nodeGraphList:
            if self._ignoreConnectivityNet(node):
                continue
            graph = self.cell.nodeGraph.get(node)
            if graph is None:
                continue
            rects = []
            if target_layer:
                rects = graph.getRectangles("^xfill_", "", target_layer)
            if len(rects) == 0:
                rects = graph.getRectangles("^xfill_", "", "")
            for rect in rects:
                if rect is None:
                    continue
                rr = rect.getCopy()
                key = (node, rr.layer, rr.x1, rr.y1, rr.x2, rr.y2)
                if key in seen:
                    continue
                seen.add(key)
                anchors.append((node, rr))
        for node, port in self.cell.ports.items():
            if self._ignoreConnectivityNet(node):
                continue
            if port is None:
                continue
            rr = port.get(target_layer) if target_layer else port.get()
            if rr is None:
                rr = port.get()
            if rr is None:
                continue
            rr = rr.getCopy()
            key = (node, rr.layer, rr.x1, rr.y1, rr.x2, rr.y2)
            if key in seen:
                continue
            seen.add(key)
            anchors.append((node, rr))
        return anchors

    def _ignoreConnectivityNet(self, net_name):
        #- the LAST segment: a child's internal net is qualified by the
        #- instance it belongs to (`x1/x2/xfill_...`), and testing the
        #- whole string would stop ignoring fill the moment it came from
        #- one level down
        return bool(net_name) and str(net_name).rsplit("/", 1)[-1].startswith("xfill_")

    def _findRoot(self, parent, idx):
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def _unionRoots(self, parent, a, b):
        ra = self._findRoot(parent, a)
        rb = self._findRoot(parent, b)
        if ra != rb:
            parent[rb] = ra

    def _netSeeds(self, indices, shapes, seeds=None):
        """Which rects a net is KNOWN to be on, inside one component.

        Two sources, and both are needed. A rect can carry a net of its
        own, and an ANCHOR -- a port or a node-graph rect -- can land on
        a rect that carries none. The second is how a component made
        entirely of unattributed metal comes to be reported as a short
        in the first place, so a reporter that ignores it can only ever
        describe the shorts that were already obvious.
        """
        seeds = seeds or {}
        out = {}
        for idx in indices:
            net = getattr(shapes[idx], "net", "")
            if not net or self._ignoreConnectivityNet(net):
                net = seeds.get(idx, "")
            if net and not self._ignoreConnectivityNet(net):
                out[idx] = net
        return out

    def _shortChains(self, indices, adjacency, shapes, nets, seeds=None,
                     limit=3, hops=14):
        """The rectangle-by-rectangle path from one net to the other.

        A BRIDGE line names two rects that touch and carry different
        labels. That is the whole story when the short is a wire laid
        across another wire, and NO story at all when the two nets are
        joined through a run of metal that carries no net -- there is no
        adjacency anywhere along it whose two ends disagree, so the
        reporter printed nothing and left a component of several hundred
        rectangles with no lead in it.

        This says it the other way round: walk the component from a rect
        the first net is known to be on until a rect the second net is
        known to be on is reached, and print the path. Every rect on it
        is a real rectangle at a real coordinate, so the reader can
        follow it in the layout; the ones in the middle are exactly the
        unattributed metal the BRIDGE view could not name.

        Shortest path, breadth first, so the run reported is the most
        direct one rather than a tour of the component.
        """
        from collections import deque

        known = self._netSeeds(indices, shapes, seeds)
        if not known:
            return []
        by_net = defaultdict(list)
        for idx, net in known.items():
            by_net[net].append(idx)

        chains = []
        for i, a in enumerate(nets):
            for b in nets[i + 1:]:
                starts = by_net.get(a, ())
                targets = set(by_net.get(b, ()))
                if not starts or not targets:
                    continue
                prev = {idx: None for idx in starts}
                queue = deque(starts)
                hit = None
                while queue and hit is None:
                    cur = queue.popleft()
                    for nxt in adjacency.get(cur, ()):
                        if nxt in prev:
                            continue
                        prev[nxt] = cur
                        if nxt in targets:
                            hit = nxt
                            break
                        queue.append(nxt)
                if hit is None:
                    continue
                path = []
                node = hit
                while node is not None:
                    path.append(node)
                    node = prev[node]
                path.reverse()
                #- a long chain is still readable at its ends: the two
                #- named rects are what identifies the nets, and the
                #- middle is what the reader walks
                if len(path) > hops:
                    path = path[:hops // 2] + [None] + path[-(hops // 2):]
                chains.append({
                    "nets": [a, b],
                    "hops": len(path),
                    "path": [None if idx is None else {
                        "layer": shapes[idx].layer,
                        "rect": [int(shapes[idx].x1), int(shapes[idx].y1),
                                 int(shapes[idx].x2), int(shapes[idx].y2)],
                        "net": known.get(idx, ""),
                        "owner": self._getShapeOwner(shapes[idx]),
                    } for idx in path],
                })
                if len(chains) >= limit:
                    return chains
        return chains

    def _shortBridges(self, indices, adjacency, shapes, limit=8, seeds=None):
        """Where two nets actually touch, rectangle by rectangle.

        A shorted component says *that* two nets are joined. This says
        *where*. Every rectangle that carries a net of its own is a seed;
        a breadth first sweep from all seeds at once labels the rest with
        whichever net reaches it first, so a wire with no net attribution
        of its own — a via pad, a piece of a guard — belongs to whatever
        it hangs off. Any adjacency whose two ends carry different labels
        is then a place the short is made, and cutting all of them would
        separate the nets.

        The labels of unattributed metal are a guess, so the *rectangles*
        reported are exact and the *net named on each side* is the nearest
        attribution rather than a proof. That is still the difference
        between a coordinate to look at and six hundred rectangles.
        """
        from collections import deque

        label = dict(self._netSeeds(indices, shapes, seeds))
        queue = deque(label)
        if not queue:
            return []

        while queue:
            i = queue.popleft()
            for j in adjacency.get(i, ()):
                if j in label:
                    continue
                label[j] = label[i]
                queue.append(j)

        bridges = []
        seen = set()
        for i in indices:
            li = label.get(i)
            if li is None:
                continue
            for j in adjacency.get(i, ()):
                lj = label.get(j)
                if lj is None or lj == li or j < i:
                    continue
                a, b = shapes[i], shapes[j]
                key = (li, lj, a.layer, b.layer,
                       int(a.x1), int(a.y1), int(b.x1), int(b.y1))
                if key in seen:
                    continue
                seen.add(key)
                bridges.append({
                    "nets": sorted((li, lj)),
                    "a": {
                        "layer": a.layer,
                        "rect": [int(a.x1), int(a.y1), int(a.x2), int(a.y2)],
                        "route": self._getRouteSource(a),
                        "owner": self._getShapeOwner(a),
                    },
                    "b": {
                        "layer": b.layer,
                        "rect": [int(b.x1), int(b.y1), int(b.x2), int(b.y2)],
                        "route": self._getRouteSource(b),
                        "owner": self._getShapeOwner(b),
                    },
                })
        #- the same pair of nets can meet in many places; show a few of
        #- each rather than eight instances of one
        bridges.sort(key=lambda x: (x["nets"], x["a"]["rect"]))
        out, per_pair = [], defaultdict(int)
        for bridge in bridges:
            pair = tuple(bridge["nets"])
            if per_pair[pair] >= 2:
                continue
            per_pair[pair] += 1
            out.append(bridge)
            if len(out) >= limit:
                break
        return out

    def check(self, target_layer=""):
        shapes = [
            rect for rect in self.cell._collectPhysicalRects()
            if self.cell._isConnectivityPropagationLayer(getattr(rect, "layer", ""))
        ]
        parent = list(range(len(shapes)))
        #- keep the edges, not just the union. A short report that says
        #- which nets ended up in one component tells you nothing about
        #- where they meet, and a component of six hundred rectangles is
        #- not something you find the bridge in by eye
        adjacency = defaultdict(list)

        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                if not self.cell._rectsTouchOrOverlap(shapes[i], shapes[j]):
                    continue
                if not self.cell._layersConnectForConnectivity(shapes[i].layer, shapes[j].layer):
                    continue
                adjacency[i].append(j)
                adjacency[j].append(i)
                self._unionRoots(parent, i, j)

        components = defaultdict(list)
        component_indices = defaultdict(list)
        for idx, rect in enumerate(shapes):
            root = self._findRoot(parent, idx)
            components[root].append(rect)
            component_indices[root].append(idx)

        anchors = self._collectNetAnchorRects(target_layer)
        net_components = defaultdict(set)
        component_nets = defaultdict(set)
        unmatched = defaultdict(list)

        for comp_id, rects in components.items():
            for rect in rects:
                net_name = getattr(rect, "net", "")
                if net_name and not self._ignoreConnectivityNet(net_name):
                    component_nets[comp_id].add(net_name)

        #- WHICH RECT the anchor lands on, not merely that it landed.
        #- A component whose rects carry no net of their own still gets
        #- two nets tagged on it this way, and the bridge reporter --
        #- which seeded only from rect nets -- then had nothing to say
        #- about it at all. A component of 868 rectangles with no bridge
        #- line is not a lead, it is noise.
        #- EVERY component the anchor reaches, not the first one found.
        #-
        #- A terminal is a rectangle, not a point, and a rectangle can
        #- sit across a gap: the pin is then itself the place the net
        #- comes apart. Stopping at the first component hid exactly that
        #- case -- the split the reader most wants to be told about is
        #- the one where the break is under the pin -- and it made the
        #- report depend on the order components happened to be built
        #- in, which is no property of the layout at all.
        anchor_seed = {}
        for net_name, anchor in anchors:
            matched = False
            if not self.cell._isConnectivityPropagationLayer(anchor.layer):
                unmatched[net_name].append(anchor)
                continue
            for comp_id, idxs in component_indices.items():
                for idx in idxs:
                    rect = shapes[idx]
                    if not self.cell._layersConnectForConnectivity(anchor.layer, rect.layer):
                        continue
                    if not self.cell._rectsTouchOrOverlap(anchor, rect):
                        continue
                    net_components[net_name].add(comp_id)
                    component_nets[comp_id].add(net_name)
                    anchor_seed.setdefault(idx, net_name)
                    matched = True
                    break
            if not matched:
                unmatched[net_name].append(anchor)

        shorts = []
        for comp_id, nets in component_nets.items():
            if len(nets) > 1:
                rects = components[comp_id]
                bounds = Cell.calcBoundingRectFromList(rects, False)
                route_sources = []
                route_seen = set()
                for rect in rects:
                    source = self._getRouteSource(rect)
                    if source is None:
                        continue
                    source_name = source.get("name", "") or source.get("net", "")
                    if source.get("debug_internal", False) or self._ignoreConnectivityNet(source_name):
                        continue
                    key = (
                        source["name"],
                        source["layer"],
                        source["route"],
                        source["options"],
                        source.get("debug_callsite", ""),
                        source.get("debug_command", ""),
                    )
                    if key in route_seen:
                        continue
                    route_seen.add(key)
                    route_sources.append(source)
                shorts.append({
                    "component": comp_id,
                    "nets": sorted(nets),
                    "rect_count": len(rects),
                    "bounds": bounds,
                    "routes": route_sources,
                    "bridges": self._shortBridges(
                        component_indices[comp_id], adjacency, shapes,
                        seeds=anchor_seed),
                    "chains": self._shortChains(
                        component_indices[comp_id], adjacency, shapes,
                        sorted(nets), seeds=anchor_seed),
                })

        opens = []
        for net_name in self.cell.nodeGraphList:
            if self._ignoreConnectivityNet(net_name):
                continue
            comp_ids = sorted(
                comp_id for comp_id, nets in component_nets.items() if net_name in nets
            )
            if len(comp_ids) == 0:
                opens.append({
                    "net": net_name,
                    "type": "unmatched",
                    "anchors": len(unmatched.get(net_name, [])),
                })
            elif len(comp_ids) > 1:
                opens.append({
                    "net": net_name,
                    "type": "split",
                    "components": comp_ids,
                })

        components_bbox = {
            cid: Cell.calcBoundingRectFromList(rs, False)
            for cid, rs in components.items()
        }

        # Per-net anchor rects (instance-port locations). Used by the GUI to
        # draw flight lines between actual transistor ports instead of
        # component bbox centres.
        net_anchor_rects = defaultdict(list)
        for net_name, rect in anchors:
            net_anchor_rects[net_name].append(rect)

        return {
            "shorts": shorts,
            "opens": opens,
            "component_nets": component_nets,
            "net_components": net_components,
            "unmatched": unmatched,
            "components_bbox": components_bbox,
            "net_anchor_rects": net_anchor_rects,
            "component_count": len(components),
            "shape_count": len(shapes),
        }

    def routeShorts(self, target_layer=""):
        result = self.check(target_layer)
        route_shorts = []
        for short in result.get("shorts", []):
            routes = short.get("routes", [])
            if not routes:
                continue

            external_routes = [route for route in routes if not route.get("debug_internal", False)]
            if len(external_routes) == 0:
                continue

            external_nets = [net for net in short.get("nets", []) if not re.match(r"^xfill_.*_dummy_", net)]
            if len(external_nets) < 2:
                continue

            filtered_short = dict(short)
            filtered_short["nets"] = external_nets
            filtered_short["routes"] = external_routes
            filtered_short["route_count"] = len(external_routes)
            route_shorts.append(filtered_short)
        return {
            "shorts": route_shorts,
            "component_count": result.get("component_count", 0),
            "shape_count": result.get("shape_count", 0),
        }

    def reportShorts(self, target_layer=""):
        result = self.check(target_layer)
        for short in result["shorts"]:
            bounds = short["bounds"]
            route_desc = "none"
            if short.get("routes"):
                route_desc = "; ".join(
                    f"{route['name']}[{route['layer']} {route['route']} {route['options']}]"
                    + (f" cmd={route['debug_command']}" if route.get("debug_command") else "")
                    + (f" at {route['debug_callsite']}" if route.get("debug_callsite") else "")
                    for route in short["routes"]
                )
            self.log.warning(
                f"SHORT component={short['component']} nets={','.join(short['nets'])} "
                f"bounds=({bounds.x1},{bounds.y1})-({bounds.x2},{bounds.y2}) rects={short['rect_count']} "
                f"routes={route_desc}"
            )
            for bridge in short.get("bridges", ()):
                self.log.warning("  " + self.describeBridge(bridge))
            for chain in short.get("chains", ()):
                self.log.warning("  " + self.describeChain(chain))
        return result["shorts"]

    @staticmethod
    def describeBridge(bridge):
        """One line naming the two rectangles a short is made across."""
        def side(s):
            text = (f"{s['layer']} ({s['rect'][0]},{s['rect'][1]})-"
                    f"({s['rect'][2]},{s['rect'][3]})")
            route = s.get("route")
            if route:
                where = route.get("debug_callsite", "")
                text += f" [{route.get('name','')} {route.get('options','')}"
                text += f" at {where}]" if where else "]"
            elif s.get("owner"):
                text += f" [{s['owner']}]"
            return text
        return (f"BRIDGE {'|'.join(bridge['nets'])}: "
                f"{side(bridge['a'])} touches {side(bridge['b'])}")

    @staticmethod
    def describeChain(chain):
        """The run of metal that joins two nets, rect by rect."""
        def hop(h):
            if h is None:
                return "..."
            text = (f"{h['layer']} ({h['rect'][0]},{h['rect'][1]})-"
                    f"({h['rect'][2]},{h['rect'][3]})")
            if h.get("net"):
                text += f" ={h['net']}"
            if h.get("owner"):
                text += f" [{h['owner']}]"
            return text
        return (f"CHAIN {'|'.join(chain['nets'])} in {chain['hops']} hops: "
                + " -> ".join(hop(h) for h in chain["path"]))

    def reportOpens(self, target_layer=""):
        result = self.check(target_layer)
        for open_net in result["opens"]:
            if open_net["type"] == "split":
                self.log.warning(f"OPEN net={open_net['net']} split_components={open_net['components']}")
            else:
                self.log.warning(f"OPEN net={open_net['net']} unmatched_anchors={open_net['anchors']}")
        return result["opens"]
