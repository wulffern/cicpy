######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2026-08-05
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################
"""Assert that coordinates leaving cicpy sit on the technology grid.

cicpy computes coordinates with ordinary Python arithmetic, so nothing in
the data model keeps them on grid.  This module is the check at the
output boundary: every coordinate written by :class:`MagicPrinter` or by
the ``.cic`` writer must be an integer multiple of the grid.

The grid is not a constant.  It is the tech file's ``technology->grid``,
which is in nanometre, converted to the ångström that coordinates are
stored in.  ``technology->gamma`` is the multiplier for rule values and
does not enter here.

Not every tech file has a grid to answer to.  The ones that only drive
svg or another view of a design that was drawn elsewhere can set
``technology->gridcheck`` to ``false`` and are then left alone.

The check is on by default and raises :class:`OffGridError`.  Set
``CICPY_GRID_CHECK=warn`` to log every violation and keep going, or
``CICPY_GRID_CHECK=off`` to disable it.
"""

import logging
import os

log = logging.getLogger("gridcheck")

CHECK_ENV = "CICPY_GRID_CHECK"

#- Keys of a Rect in the .cic json, in the order they are reported
COORD_KEYS = ("x1", "y1", "x2", "y2")

#- Coordinates are ångström, the tech file states the grid in nanometre
ANGSTROM_PER_NM = 10


class OffGridError(Exception):
    """A coordinate that is about to be written is not on the grid."""


def gridFromRules(rules):
    """Database units per grid step, from the tech file.

    ``technology->grid`` is nanometre, coordinates are ångström, so the
    grid step is ten times the stated value.  ``technology->gamma`` is
    the multiplier for rule values and has nothing to do with the grid.
    Returns 0 when there are no rules, which disables the check.
    """
    if rules is None:
        return 0
    if not getattr(rules, "gridcheck", True):
        return 0
    grid = getattr(rules, "grid", 0) or 0
    #- round, not truncate, so a sub-nanometre grid such as 0.5 nm
    #- survives as 5 ångström instead of collapsing to zero
    return int(round(float(grid) * ANGSTROM_PER_NM))


def checkMode():
    mode = os.environ.get(CHECK_ENV, "error").lower()
    if mode not in ("error", "warn", "off"):
        log.warning(f"Unknown {CHECK_ENV}={mode}, using 'error'")
        return "error"
    return mode


class GridChecker:
    """Checks coordinates against the grid on their way out.

    Parameters
    ----------
    rules : Rules
        Technology rules; the grid and gamma come from here.
    output : str
        What is being written, for the message, e.g. ``"magic"`` or the
        name of the ``.cic`` file.
    """

    def __init__(self, rules, output=""):
        self.grid = gridFromRules(rules)
        self.gridsource = "grid %s nm" % (getattr(rules, "grid", "?"),)
        self.output = output
        self.mode = checkMode()
        self.cell = ""
        self.violations = list()

    def enabled(self):
        return self.grid > 0 and self.mode != "off"

    def setCell(self, name):
        self.cell = name

    def onGrid(self, v):
        if v is None:
            return True
        if isinstance(v, bool):
            return False
        if not isinstance(v, (int, float)):
            return True
        if v != int(v):
            return False
        return int(v) % self.grid == 0

    def check(self, x1, y1, x2, y2, layer="", net="", what="rect", where=""):
        """Check one rectangle.  Raises unless the mode says otherwise."""

        if not self.enabled():
            return

        coords = (x1, y1, x2, y2)
        bad = [(k, v) for k, v in zip(COORD_KEYS, coords) if not self.onGrid(v)]
        if not bad:
            return

        message = self._message(bad, coords, layer, net, what, where)
        self.violations.append(message)

        if self.mode == "error":
            raise OffGridError(message)
        log.warning(message)

    def checkRect(self, r, what="rect", where=""):
        """Check a :class:`Rect` object."""
        self.check(r.x1, r.y1, r.x2, r.y2,
                   layer=getattr(r, "layer", ""),
                   net=getattr(r, "net", ""),
                   what=what, where=where)

    def _message(self, bad, coords, layer, net, what, where):
        offending = ", ".join(
            "%s=%s" % (k, self._fmt(v)) for k, v in bad)
        rect = " ".join(
            "%s=%s" % (k, self._fmt(v)) for k, v in zip(COORD_KEYS, coords))

        head = "Off grid"
        if self.output:
            head += " writing " + self.output
        if self.cell:
            head += " cell=" + self.cell
        if where:
            head += " " + where

        return ("%s: %s layer=%s net=%s %s [%s]"
                " is not a multiple of %d database units (%s)") % (
                    head, what,
                    layer if layer != "" else "<none>",
                    net if net != "" else "<none>",
                    offending, rect, self.grid, self.gridsource)

    @staticmethod
    def _fmt(v):
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)


def checkJsonOnGrid(obj, rules, output=""):
    """Check every rectangle in a ``.cic`` json tree.

    Walks the design dictionary that is about to be serialised.  Any
    object carrying ``x1``/``y1``/``x2``/``y2`` is a rectangle, which
    covers rects, ports, routes, instances and the cell extents.
    """

    checker = GridChecker(rules, output=output)
    if not checker.enabled():
        return checker

    def walk(o, cell):
        if isinstance(o, dict):
            name = o.get("name")
            if "children" in o and isinstance(name, str) and name != "":
                cell = name
            if all(k in o for k in COORD_KEYS):
                checker.setCell(cell)
                checker.check(o["x1"], o["y1"], o["x2"], o["y2"],
                              layer=o.get("layer", ""),
                              net=o.get("net", ""),
                              what=o.get("class", "rect"),
                              where=_instanceName(o))
            for v in o.values():
                walk(v, cell)
        elif isinstance(o, list):
            for v in o:
                walk(v, cell)

    walk(obj, "")
    return checker


def _instanceName(o):
    name = o.get("instanceName") or o.get("name")
    if name:
        return "name=" + str(name)
    return ""
