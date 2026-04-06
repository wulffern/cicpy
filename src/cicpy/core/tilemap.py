#!/usr/bin/env python3
######################################################################
##  The MIT License (MIT)
##  Copyright (c) 2020 Carsten Wulff Software, Norway
######################################################################
"""
TileMap: layer-indexed occupancy map built after placement and dummy-device
routing.  Consulted by addConnectivityRoute to detect conflicts *before* a
route is committed to the layout.

Two rects conflict when:
  - they overlap in XY, AND
  - their layers are the same or directly adjacent in the layer stack
    (e.g. M1 ↔ VIA1, VIA1 ↔ M2), AND
  - they carry different, non-empty net names.
"""

import logging
from .rules import Rules


class RouteConflictError(Exception):
    """Raised when a new route would create a short with an existing net."""
    pass


class TileMap:
    """
    Occupancy snapshot for all labelled rects present in the layout after
    ``afterPlace`` (including ``routeDummyDevices``).

    Usage in the layout flow::

        # in LayoutCell.layout(), between afterPlace and beforeRoute:
        self.buildTileMap()

        # in addConnectivityRoute(), after getRectangles():
        conflicts = self._tile_map.check(layer, rects, node)
        for c in conflicts:
            self.log.error("TILE CONFLICT ...")
    """

    def __init__(self):
        self.log = logging.getLogger("TileMap")
        # layer_name -> list of (Rect_copy, net_name, source_description)
        self._entries: dict = {}
        self._shape_count: int = 0

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def populate(self, layout_cell):
        """
        Walk the full child tree of *layout_cell* and record every rect that
        has both a layer and a net label.  Translates rect coordinates into
        the parent cell's coordinate space so that instance-level rects are
        compared in the correct absolute positions.

        Call this after ``afterPlace`` and before ``beforeRoute``.
        """
        self._entries = {}
        self._shape_count = 0
        self._walk(layout_cell, 0, 0, set())
        self.log.info(
            "TileMap: populated %d labelled shapes across %d layers: %s",
            self._shape_count,
            len(self._entries),
            list(self._entries.keys()),
        )

    def _walk(self, obj, dx: int, dy: int, visited: set, inherited_net: str = ""):
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)

        # Routes carry a net for all their child rects
        obj_net = getattr(obj, "net", "") or ""
        if not obj_net:
            obj_net = inherited_net

        children = getattr(obj, "children", [])
        for child in children:
            if child is None:
                continue
            # Logical constructs – skip
            if (hasattr(child, "isPort") and child.isPort()) or \
               (hasattr(child, "isInstancePort") and child.isInstancePort()):
                continue
            # Recurse into instances (apply translation)
            if child.isInstance():
                lc = getattr(child, "layoutcell", None)
                if lc is not None:
                    self._walk(lc, dx + child.x1, dy + child.y1, visited)
                continue
            # Recurse into cells / routes; propagate net if child is a Route
            if child.isCell():
                child_net = getattr(child, "net", "") or obj_net
                self._walk(child, dx, dy, visited, inherited_net=child_net)
                continue
            # Record physical rects that carry a net label
            if child.isRect():
                net = getattr(child, "net", "") or obj_net
                layer = getattr(child, "layer", "") or ""
                if not net or not layer:
                    continue
                rr = child.getCopy()
                rr.translate(dx, dy)
                info = self._source_desc(child)
                if layer not in self._entries:
                    self._entries[layer] = []
                self._entries[layer].append((rr, net, info))
                self._shape_count += 1

        visited.discard(obj_id)

    def _source_desc(self, rect) -> str:
        """Return a human-readable string identifying where the rect came from."""
        roi = getattr(rect, "route_owner_info", None)
        if roi:
            cmd  = roi.get("debug_command", "")
            site = roi.get("debug_callsite", "")
            name = roi.get("name", "")
            parts = [p for p in (name, cmd) if p]
            desc = " | ".join(parts)
            if site:
                desc += f" at {site}"
            return desc
        return ""

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def _direct_connect(self, layer1: str, layer2: str) -> bool:
        """
        Return True if *layer1* and *layer2* are the same layer, or are
        directly adjacent in the process stack (one hop, e.g. M1↔VIA1).
        """
        if layer1 == layer2:
            return True
        rules = Rules.getInstance()
        if rules is None:
            return False
        try:
            lo1 = rules.getLayer(layer1)
            lo2 = rules.getLayer(layer2)
            if lo1 is None or lo2 is None:
                return False
            if getattr(lo1, "next", "")     == layer2:
                return True
            if getattr(lo1, "previous", "") == layer2:
                return True
            if getattr(lo2, "next", "")     == layer1:
                return True
            if getattr(lo2, "previous", "") == layer1:
                return True
        except Exception:
            pass
        return False

    def conflicts(self, layer: str, rect, net: str) -> list:
        """
        Return a list of ``(existing_rect, existing_net, source_desc)`` tuples
        where *existing_net* differs from *net* and the rects would be
        electrically connected (overlapping XY on a connected layer pair).
        """
        if not net or not layer:
            return []
        result = []
        for entry_layer, entries in self._entries.items():
            if not self._direct_connect(layer, entry_layer):
                continue
            for existing_rect, existing_net, info in entries:
                if existing_net == net:
                    continue
                if rect.overlaps(existing_rect):
                    result.append((existing_rect, existing_net, info))
        return result

    def check(self, layer: str, rects: list, net: str) -> list:
        """
        Check a list of candidate rects for conflicts with the occupied map.

        Each rect may carry its own ``.layer`` attribute (used when
        ``addConnectivityRoute`` falls back from the requested layer to an
        available one); if absent, *layer* is used as default.

        Returns a list of
        ``(candidate_rect, existing_rect, existing_net, source_desc)`` tuples.
        """
        all_conflicts = []
        for rect in rects:
            rect_layer = getattr(rect, "layer", "") or layer
            self.log.debug(
                "TileMap.check: net=%s layer_arg=%s rect_layer=%s rect=(%s,%s)-(%s,%s)",
                net, layer, rect_layer, rect.x1, rect.y1, rect.x2, rect.y2,
            )
            for existing_rect, existing_net, info in self.conflicts(
                rect_layer, rect, net
            ):
                all_conflicts.append((rect, existing_rect, existing_net, info))
        return all_conflicts
