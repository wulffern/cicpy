#!/usr/bin/env python3
"""Cell classes backed by cicpy's own LayoutCell."""
from ...core.layoutcell import LayoutCell as _CicpyLayoutCell
from ..registry import cicclass


@cicclass("cIcCore::LayoutCell", "Layout::LayoutCell")
class LayoutCell(_CicpyLayoutCell):
    """cicpy's LayoutCell, under the name object files use for it."""

    def __init__(self, name=""):
        #- cicpy's LayoutCell takes no name; Cell does
        super().__init__()
        if name:
            self.name = name
        #- object files set this by property; the C++ name has no `set`
        self.patterns = {}


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
