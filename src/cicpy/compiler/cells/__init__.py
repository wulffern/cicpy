#!/usr/bin/env python3
"""The cell classes an object file may name in its `class` key.

cicpy's own LayoutCell already implements most of what object files
call -- addDirectedRoute, addRectangle, addRouteRing, addPowerRing and
the rest -- because it grew up reading the .cic files ciccreator
writes. So the classes here are mostly THIN: they register an existing
cicpy class under the name ciccreator knows it by.

What is not thin is PatternTile, which has no cicpy equivalent.
"""
from ..registry import register
from .layoutcells import (LayoutCell, LayoutDigitalCell, LayoutRotateCell)
from .patterntile import PatternTile

__all__ = ["LayoutCell", "LayoutDigitalCell", "LayoutRotateCell", "PatternTile"]
