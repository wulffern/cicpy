######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2026-8-13
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
"""What is in the way, as a cell in its own right.

A router needs to know what its wire would run into, and the honest
answer lives at every depth of the hierarchy: a JNWTR standard cell
publishes its pins and its two M4 supply bars, while the M2 and M3
that block a lane are inside the cut cells it places. Measured on
LELO_TEMP_DIG -- `tracks`, `blockers`, the maze router and the
connectivity check all called those columns free, and the GDS was the
first thing that knew otherwise.

THE VIEW IS A CELL, NOT A LIST. A flat list has to be built per cell
and carries a copy of every descendant, so a strip of eight standard
cells over four device cells copies those devices eight times to say
what one of them contains. A `BlockCell` holds a cell's OWN metal and
a `BlockCellInstance` per cell it places, which points at that cell's
BlockCell -- one per real cell, shared by every instance of it. The
structure is the hierarchy; only the leaves are copied, once.

It is deliberately NOT the layout: a BlockCell is built beside the
real cell (which is its `parent`), never inside it, so `children` --
what placement, bounding boxes, ports and both writers read -- is
untouched by asking.
"""
import logging

from .layoutcell import LayoutCell
from .instance import Instance

log = logging.getLogger("BlockCell")

#- WHAT A ROUTE CAN RUN INTO: metal, and the cuts between metals. A
#- marker or an implant stops nothing, and diffusion and poly are not
#- on any layer a route uses -- whatever they connect to reaches li,
#- and the li is in the view already. Copying them made the view three
#- times its size to say nothing new.
CONDUCTORS = ("METAL",)


class BlockCellInstance(Instance):
    """One BlockCell placed inside another, by offset and mirror.

    The same object as a layout instance minus the netlist: a block
    view has no terminals, no ports and no subcircuit, only a place to
    put a cell that is already built.
    """

    def __init__(self, block, dx=0, dy=0, mx=False, my=False):
        super().__init__()
        self.block = block
        self.cell = getattr(block, "name", "")
        self.instanceName = self.cell
        self.layoutcell = block
        self._cell_obj = block
        #- the printer names a reference by `name`, as it does for a
        #- layout instance
        self.name = self.cell
        self.moveTo(int(dx), int(dy))
        self.mx = bool(mx)
        self.my = bool(my)
        if mx:
            self.angle = "MY"
        elif my:
            self.angle = "MX"

    def rects(self, dx=0, dy=0, mx=False, my=False):
        """This instance's contents, in the caller's frame."""
        return self.block.rects(dx + int(self.x1), dy + int(self.y1),
                                mx != self.mx, my != self.my,
                                frame=True)


class BlockCell(LayoutCell):
    """A cell's conductors, and references to what it places."""

    def __init__(self, cell):
        super().__init__()
        self.name = getattr(cell, "name", "")
        #- the real cell is the PARENT: a block view is derived from
        #- it and answers for it, and saying so keeps the two joined
        #- without the real cell holding anything extra.
        self.parent = cell
        self.own = []
        self.places = []

    #- -----------------------------------------------------------------
    #- building, once per real cell
    #- -----------------------------------------------------------------

    @classmethod
    def of(cls, cell):
        """The block view of `cell`, built once and remembered.

        REMEMBERED IS NOT FOREVER: a cell grows all through its build,
        and a view taken before its instances were placed answers for
        an empty cell. Measured: every corridor a story asked for came
        back as the whole width of the block, because the first thing
        to ask had asked too early. The stamp is what the view was
        built from -- how many children, and the box they made -- and
        a cell that has changed since gets a new one.
        """
        if cell is None:
            return None
        stamp = cls.stamp(cell)
        block = getattr(cell, "_blockcell", None)
        if block is None or getattr(cell, "_blockcell_stamp", None) != stamp:
            block = cls(cell)
            #- stored BEFORE the walk, so a cell that reaches itself
            #- through its own hierarchy finds the one being built
            #- rather than recursing forever
            cell._blockcell = block
            cell._blockcell_stamp = stamp
            block.build(cell)
        return block

    @staticmethod
    def stamp(cell):
        return (len(getattr(cell, "children", []) or []),
                int(cell.x1), int(cell.y1), int(cell.x2), int(cell.y2))

    def build(self, cell, into=None):
        """Walk `cell`, collecting its metal and what it places.

        THROUGH THE GROUPS TOO. A cell's instances are not always its
        direct children: a placed design keeps them in CellGroups and
        Stacks, and `children` holds the group. Walking only the top
        level, the view of LELO_TEMP_DIG came back EMPTY -- no metal,
        no cells, eight instances one level down -- and every question
        asked of it ("what is free here?") answered "everything".
        """
        for child in getattr(cell, "children", []) or []:
            if child is None:
                continue
            if hasattr(child, "isInstance") and child.isInstance():
                sub = (getattr(child, "layoutcell", None)
                       or getattr(child, "_cell_obj", None))
                if sub is None or sub is cell:
                    continue
                angle = getattr(child, "angle", "") or ""
                self.place(sub, child.x1, child.y1,
                           angle == "MY", angle == "MX", hidden=False)
                continue
            if hasattr(child, "isRect") and child.isRect() \
                    and self.blocking(child):
                r = child.getCopy()
                r.device_metal = True
                self.own.append(r)
                self.add(r)
                continue
            #- a group or a stack: its members are the cell's, in the
            #- cell's own frame, so walk straight into it
            if getattr(child, "children", None) and child is not cell:
                self.build(child)
        #- and the hierarchy `children` does not name. A reader may
        #- keep it elsewhere -- the magic one keeps `use` records out
        #- of children on purpose -- and says so through hiddenUses().
        for sub, dx, dy, mx, my in (cell.hiddenUses() or []):
            self.place(sub, dx, dy, mx, my, hidden=True)
        self.updateBoundingRect()

    def blocks(self, out=None):
        """This block and every block below it, deepest first.

        What a printer needs: a `use` can only name a cell that has
        already been written, and it is also what makes the view
        DRAWABLE -- a BlockCell is a LayoutCell and a BlockCellInstance
        is an Instance, so the whole thing goes through the same
        printer as a real design, flightlines and all.
        """
        out = [] if out is None else out
        for inst in self.places:
            inst.block.blocks(out)
        if not any(b is self for b in out):
            out.append(self)
        return out

    def place(self, cell, dx, dy, mx=False, my=False, hidden=False):
        inst = BlockCellInstance(BlockCell.of(cell), dx, dy, mx, my)
        inst.hidden = hidden
        self.places.append(inst)
        self.add(inst)
        return inst

    @staticmethod
    def blocking(rect):
        from .rules import Rules
        layer = Rules.getInstance().getLayer(getattr(rect, "layer", ""))
        material = getattr(layer, "material", None)
        name = getattr(material, "name", str(material)).upper()
        return any(c in name for c in CONDUCTORS)

    #- -----------------------------------------------------------------
    #- asking
    #- -----------------------------------------------------------------

    def rects(self, dx=0, dy=0, mx=False, my=False, hidden_only=False,
              frame=False):
        """Every conductor below this cell, in the caller's frame.

        The copies happen HERE, once per question, from a structure
        that holds each cell's metal exactly once.

        `frame` says dx/dy place the cell's BOX, which is what an
        instance does -- a placed cell puts its box corner at the
        instance position, whatever its own origin is. Asked of the
        top of a view (`frame=False`) the answer stays in the cell's
        own coordinates, which is what its owner means by "in this
        cell's frame".
        """
        out = []
        box = (int(self.x1), int(self.y1), int(self.x2), int(self.y2)) \
            if frame else None
        if not hidden_only:
            for r in self.own:
                out.append(self.moved(r, dx, dy, mx, my, box))
        for inst in self.places:
            if hidden_only and not getattr(inst, "hidden", False):
                continue
            out += inst.rects(dx, dy, mx, my)
        return out

    @staticmethod
    def moved(rect, dx, dy, mx, my, box=None):
        """One rect, placed.

        MIRROR ABOUT THE CELL'S OWN BOX, not about zero. The two are
        the same for a cell whose box starts at its origin and differ
        by x1/y1 for every other -- and a block with a supply ring
        below y=0 is one. Measured on LELO_TEMP_CCMP: the mirrored
        comparator's metal came back 24000 low, and with it every
        answer this view gives about what is free up there.
        """
        r = rect.getCopy()
        r.device_metal = True
        x1, y1, x2, y2 = box if box else (0, 0, 0, 0)
        #- x2 (not x1 + x2) for the mirror, -x1 for the plain case:
        #- both put the box's own corner at the instance position,
        #- which is what a placed cell does.
        if mx:
            r.mirrorY(0)
            r.translate(x2, 0)
        elif box:
            r.translate(-x1, 0)
        if my:
            r.mirrorX(0)
            r.translate(0, y2)
        elif box:
            r.translate(0, -y1)
        r.translate(int(dx), int(dy))
        return r
