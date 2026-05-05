######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

"""RouteGroup — a chainable, named multi-segment route for one net.

A real bias / cascode net is rarely one shape; it is a *trunk* spanning a
row of devices, *spurs* dropping from the trunk to each device terminal,
and zero or more *exits* picking up from one trunk endpoint and running
out to a cell port or another region. Today each piece is a separate
``addConnectivityRoute`` / ``addRouteConnection`` / ``addPortOnEdge``
call with no record that they form one logical route.

``RouteGroup`` composes those existing primitives without changing them,
so the old API keeps working. Build one with::

    rg = layout.addRouteGroup("VBP4")
    rg.trunk(layer="M3", side="top", includeInstances="^xb")
    rg.exit(side="left", layer="M3")

``trunk`` uses the existing U_TOP / U_BOTTOM single-layer route which
draws a horizontal spine plus vertical drops to every matched anchor —
that is the trunk-and-spurs pattern.
"""

import logging
import re


class RouteGroup:
    """Chainable builder that emits one or more underlying routes for
    a single net. Methods return ``self`` so calls can be chained."""

    def __init__(self, layout, net: str):
        self._layout = layout
        self._net = net
        self._trunk_layer = None
        self._trunk_side = None
        self._segments = []  # list of dicts; for inspection / debug
        self._log = logging.getLogger("RouteGroup")

    # ---------------------------------------------------------------
    # Trunk + auto-spurs (single layer)
    # ---------------------------------------------------------------
    def trunk(
        self,
        layer: str,
        side: str = "top",
        includeInstances: str = "",
        excludeInstances: str = "",
        cuts: int = 2,
        options: str = "",
    ):
        """Lay a horizontal trunk on ``layer`` along the ``side`` of the
        anchor bounding box and drop a vertical spur on the same layer
        to every matched anchor.

        ``side`` accepts ``"top"`` / ``"t"`` or ``"bottom"`` / ``"b"``.
        ``includeInstances`` / ``excludeInstances`` are regex strings on
        the instance name, identical in semantics to
        ``addConnectivityRoute``. Diode-connected gates and other anchors
        are matched by exact net name (with optional ``<idx>`` bus
        suffix), so a net called ``VBP4`` will not also catch ``VBP44``.
        """
        s = side.lower()
        if s in ("top", "t"):
            route_type = "--|"   # U_TOP — trunk above, drops down
        elif s in ("bottom", "b"):
            route_type = "|--"   # U_BOTTOM — trunk below, drops up
        else:
            raise ValueError(
                f"RouteGroup.trunk: side must be top|bottom, got {side!r}"
            )

        # Anchor exactly one node per bus index: ``VBP4`` or ``VBP4<3>``
        # but not ``VBP44``.
        regex = rf"^{re.escape(self._net)}(<\d+>)?$"

        self._log.info(
            "RouteGroup(%s).trunk(layer=%s, side=%s, regex=%s)",
            self._net, layer, s, regex,
        )

        self._layout.addConnectivityRoute(
            layer, regex, route_type, options, cuts,
            excludeInstances, includeInstances,
        )

        self._trunk_layer = layer
        self._trunk_side = s
        self._segments.append({
            "kind": "trunk",
            "layer": layer,
            "side": s,
            "includeInstances": includeInstances,
            "excludeInstances": excludeInstances,
        })
        return self

    # ---------------------------------------------------------------
    # Exit — pickup from the trunk to a cell-edge port
    # ---------------------------------------------------------------
    def exit(self, side: str, layer: str = None, options: str = ""):
        """Pickup from the trunk and run to a cell-edge port.

        ``side`` selects which edge of the cell to land on
        (``top``/``bottom``/``left``/``right``). The net must already be
        declared as a port on the cell — exits exist to expose an
        already-connected net to the parent. ``layer`` defaults to the
        trunk layer.

        Implementation note: this delegates to
        ``LayoutCell.addPortOnEdge``, which both moves the port pin to
        the requested edge and emits a route from the existing port
        position to that pin.
        """
        if layer is None:
            layer = self._trunk_layer
        if layer is None:
            raise ValueError(
                "RouteGroup.exit: no layer given and no trunk has been "
                "laid yet"
            )
        s = side.lower()
        if s not in ("top", "bottom", "left", "right"):
            raise ValueError(
                f"RouteGroup.exit: side must be top|bottom|left|right, "
                f"got {side!r}"
            )

        if self._net not in getattr(self._layout, "ports", {}):
            self._log.warning(
                "RouteGroup(%s).exit: net is not a cell port; "
                "skipping exit. Declare the port in the schematic to "
                "expose this net at the cell boundary.",
                self._net,
            )
            return self

        # Vertical edges → horizontal route, horizontal edges → vertical
        route_type = "||" if s in ("top", "bottom") else "-"

        self._log.info(
            "RouteGroup(%s).exit(side=%s, layer=%s, options=%s)",
            self._net, s, layer, options,
        )

        self._layout.addPortOnEdge(layer, self._net, s, route_type, options)

        self._segments.append({
            "kind": "exit",
            "side": s,
            "layer": layer,
            "options": options,
        })
        return self

    # ---------------------------------------------------------------
    # Inspection
    # ---------------------------------------------------------------
    @property
    def net(self) -> str:
        return self._net

    @property
    def segments(self):
        """List of segment descriptors (dicts) emitted so far. Useful
        for the GUI to render what a RouteGroup will produce before it
        runs, and for tests."""
        return list(self._segments)
