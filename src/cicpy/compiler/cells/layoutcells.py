#!/usr/bin/env python3
"""Cell classes backed by cicpy's own LayoutCell."""
import logging

from ...core.layoutcell import LayoutCell as _CicpyLayoutCell
from ..registry import cicclass

log = logging.getLogger("cicpy.compiler")


@cicclass("cIcCore::LayoutCell", "Layout::LayoutCell")
class LayoutCell(_CicpyLayoutCell):
    """cicpy's LayoutCell, under the name object files use for it.

    Most object-file calls land straight on cicpy's own methods: the
    dispatcher spreads the JSON array into their positional arguments
    and the orders already agree. Where they DO NOT agree, the method
    is overridden here to unpack the array the way ciccreator's
    QJsonArray overload does -- this class is the calling convention,
    so the adaptation belongs in it and cicpy's core stays untouched.
    """

    def __init__(self, name=""):
        #- cicpy's LayoutCell takes no name; Cell does
        super().__init__()
        if name:
            self.name = name
        #- object files set this by property; the C++ name has no `set`
        self.patterns = {}

    def addConnectivityRoute(self, *args):
        """[layer, regex, routeType, options, cuts, includeInstances]

        NOT a plain spread. ciccreator reads element 5 into
        includeInstances and leaves excludeInstances empty -- there is
        no element for it -- so spreading positionally would put an
        instance filter into the exclude slot and quietly route the
        complement of what the object file asked for.
        """
        if len(args) != 1 or not isinstance(args[0], list):
            return super().addConnectivityRoute(*args)
        obj = args[0]
        if len(obj) < 3:
            log.error("addConnectivityRoute needs at least three elements")
            return None
        def at(i):
            return str(obj[i]) if len(obj) > i else ""
        return super().addConnectivityRoute(
            at(0), at(1), at(2),
            options=at(3), cuts=at(4),
            excludeInstances="", includeInstances=at(5))


@cicclass("Layout::LayoutDigitalCell")
class LayoutDigitalCell(LayoutCell):
    """A standard-cell-shaped LayoutCell.

    In ciccreator this subclass adds the digital row conventions on top
    of LayoutCell. Everything an object file calls on it is inherited,
    so until those conventions are ported it behaves as a LayoutCell --
    which is right for placement and wrong for the implicit rails.
    """


@cicclass("Layout::LayoutRotateCell")
class LayoutRotateCell(LayoutCell):
    """A LayoutCell whose contents are rotated by `rotateAngle`."""

    def __init__(self, name=""):
        super().__init__(name)
        self.rotateAngle = 0
