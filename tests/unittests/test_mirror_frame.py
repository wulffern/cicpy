"""A mirrored instance must answer the same from every level.

`checkroutes` used to give a different verdict for the same geometry
depending on which cell you asked about. The comparator pair in
LELO_TEMP reported `shorts=0` asked directly and `shorts=2` asked
through the tile that contains it, with nothing routed at either level
and magic's extractor finding no shorted port anywhere.

The cause was that the hierarchy walk flattened by TRANSLATION and then
folded the emitted flat list in place for a mirrored instance. A fold
applied after the fact is relative to where the flatten STARTED, so the
same rect came out in two different places depending on how deep the
walk had been when it reached it. A checker that depends on where you
stand cannot be trusted in either direction.

There was no test for this, which is why it survived six attempts at
fixing it by varying the fold. This is that test: the invariant is
LEVEL INDEPENDENCE, not any particular formula.

The fixture is built here rather than loaded, because the bug needs a
cell whose own content does not start at the origin -- `y1 != 0` is
exactly where a fold about the instance's placed box and a fold about
the cell's extent stop agreeing -- and no fixture in this repository
has a mirrored instance of one.
"""
import unittest

from cicpy.core.instance import Instance
from cicpy.core.layoutcell import LayoutCell
from cicpy.core.rect import Rect
from cicpy.core.rules import Rules


def _tech():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "transpile", "demo.tech")


def _rect(layer, x1, y1, x2, y2, net=""):
    r = Rect(layer, x1, y1, x2 - x1, y2 - y1)
    if net:
        r.setNet(net)
    return r


def _build():
    """LEAF < MID < TOP, with LEAF mirrored into MID.

    LEAF's content starts at y=10000, so `cell.y1` is not zero and the
    two candidate folds differ by exactly that much.

        LEAF  (own frame)          MID (after the MX fold, ycell=y2)
          B   30000..34000  --->     B    0.. 4000
          A   10000..14000  --->     A   20000..24000

    MID adds a netless bar down the right edge spanning y 0..24000. It
    abuts BOTH mirrored rects, so A and B land in one component and the
    cell has one short -- deliberately, so the assertion has something
    to count. Fold about the instance's placed box instead and A moves
    to 10000..14000 with B below the origin, the bar reaches only one of
    them, and the count changes.
    """
    leaf = LayoutCell()
    leaf.name = "MIRROR_LEAF"
    leaf.add(_rect("M1", 0, 10000, 20000, 14000, "A"))
    leaf.add(_rect("M1", 0, 30000, 20000, 34000, "B"))
    leaf.updateBoundingRect()

    mid = LayoutCell()
    mid.name = "MIRROR_MID"
    xl = Instance()
    xl.instanceName = "XL"
    xl.setCell(leaf)
    #- `setCell` fills `_cell_obj`; `setAngle` reads `layoutcell`, and
    #- with it unset the fold silently degrades to a mirror about zero.
    #- `LayoutCell.addInstance` sets both.
    xl.layoutcell = leaf
    xl.updateBoundingRect()
    xl.moveTo(0, 0)
    xl.setAngle("MX")
    mid.add(xl)
    mid.add(_rect("M1", 20000, 0, 24000, 24000))
    mid.updateBoundingRect()

    top = LayoutCell()
    top.name = "MIRROR_TOP"
    xm = Instance()
    xm.instanceName = "XM"
    xm.setCell(mid)
    xm.layoutcell = mid
    xm.updateBoundingRect()
    xm.moveTo(100000, 50000)
    top.add(xm)
    top.updateBoundingRect()
    return leaf, mid, top


def _shapes(cell, offset=(0, 0)):
    """(layer, net, box) for every collected rect, in MID's frame."""
    dx, dy = offset
    out = set()
    for r in cell._collectPhysicalRects():
        out.add((r.layer, getattr(r, "net", ""),
                 int(r.x1) - dx, int(r.y1) - dy,
                 int(r.x2) - dx, int(r.y2) - dy))
    return out


class MirrorFrame(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Rules(_tech())
        cls.leaf, cls.mid, cls.top = _build()

    def test_leaf_does_not_start_at_the_origin(self):
        """Without this the two folds agree and the test proves nothing."""
        self.assertNotEqual(int(self.leaf.y1), 0)

    def test_the_mirror_lands_where_the_cell_extent_says(self):
        boxes = {net: (y1, y2) for _, net, _, y1, _, y2 in _shapes(self.mid)
                 if net}
        self.assertEqual(boxes["B"], (0, 4000))
        self.assertEqual(boxes["A"], (20000, 24000))

    def test_same_geometry_from_both_levels(self):
        """The invariant. One rect, one transform, however deep you start."""
        self.assertEqual(_shapes(self.mid),
                         _shapes(self.top, offset=(100000, 50000)))

    def test_same_shorts_from_both_levels(self):
        mid = self.mid.checkConnectivity()
        top = self.top.checkConnectivity()
        self.assertEqual(len(mid["shorts"]), len(top["shorts"]))
        self.assertEqual([s["nets"] for s in mid["shorts"]],
                         [s["nets"] for s in top["shorts"]])

    def test_the_short_is_the_one_the_fixture_draws(self):
        """A count that agrees at zero would agree by accident."""
        shorts = self.mid.checkConnectivity()["shorts"]
        self.assertEqual([s["nets"] for s in shorts], [["A", "B"]])


def _netless_blob():
    """Two ports on one run of metal that carries no net of its own.

    This is the shape of the report the mirror bug produced: the flood
    unions every touching rect regardless of net, then tags a component
    with any net whose ANCHOR merely touches it. A blob of netless rects
    is therefore not neutral -- it is a conductor belonging to whatever
    it lies between -- and two ports on opposite ends of one blob read
    as a short.

    The BRIDGE reporter seeded only from rects that carry a net, so for
    this component it printed nothing at all, and a short with no bridge
    line under it is unreadable.
    """
    from cicpy.core.port import Port

    cell = LayoutCell()
    cell.name = "NETLESS_BLOB"
    for i in range(4):
        cell.add(_rect("M1", i * 10000, 0, (i + 1) * 10000, 2000))
    #- INSIDE one rect each, not abutting the next: an anchor is bound
    #- to the first rect of the component it touches, and a port that
    #- spans a seam would be bound to either of two.
    for name, x in (("A", 1000), ("B", 31000)):
        p = Port(name, "M1", _rect("M1", x, 0, x + 8000, 2000))
        cell.ports[name] = p
        cell.add(p)
    cell.updateBoundingRect()
    return cell


class NetlessBlobIsExplained(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Rules(_tech())
        cls.cell = _netless_blob()
        cls.short = cls.cell.checkConnectivity()["shorts"][0]

    def test_the_short_is_reported(self):
        self.assertEqual(self.short["nets"], ["A", "B"])

    def test_a_chain_is_reported(self):
        """The point. Something has to name the metal in between."""
        chains = self.short["chains"]
        self.assertTrue(chains, "a two-net component with no chain is noise")
        self.assertEqual(chains[0]["nets"], ["A", "B"])
        #- all four rects, end to end
        self.assertEqual(chains[0]["hops"], 4)
        line = LayoutCell.describeChain(chains[0])
        self.assertIn("CHAIN A|B", line)
        self.assertIn("(0,0)-(10000,2000)", line)
        self.assertIn("(30000,0)-(40000,2000)", line)


def _name_collision():
    """A child with an internal net whose NAME the parent also uses.

    LELOTEMP_OTAR calls its own internal drain nodes VD1 and VD2.
    LELOTEMP_BIAS_IBP, four levels up, has top-level nets of those
    names too -- and BIAS_IBP's VD1 arrives at OTAR as VIN, so the two
    conductors have nothing to do with each other. Left bare, the
    child's label collides with the parent's and the net is reported
    OPEN, split across two components that never touch. netgen matched
    the same layout uniquely.

    Here: LEAF has a boundary net IN and an internal net VD1. TOP wires
    LEAF's IN to a net of its own called VD1, and has a second, separate
    piece of real VD1 elsewhere. Three conductors, and only two of them
    are the same net.
    """
    from cicpy.core.port import Port

    leaf = LayoutCell()
    leaf.name = "COLLIDE_LEAF"
    leaf.add(_rect("M1", 0, 0, 10000, 2000, "IN"))
    leaf.add(_rect("M1", 0, 10000, 10000, 12000, "OUT"))
    #- INTERNAL: no port publishes it, so its name is the child's alone
    leaf.add(_rect("M1", 0, 20000, 10000, 22000, "VD1"))
    for name, y in (("IN", 0), ("OUT", 10000)):
        p = Port(name, "M1", _rect("M1", 1000, y, 9000, y + 2000))
        leaf.ports[name] = p
        leaf.add(p)
    leaf.updateBoundingRect()

    top = LayoutCell()
    top.name = "COLLIDE_TOP"
    xl = Instance()
    xl.instanceName = "XL"
    xl.setCell(leaf)
    xl.layoutcell = leaf
    xl.updateBoundingRect()
    xl.moveTo(0, 0)
    #- the wiring: LEAF's IN is what TOP calls VD1
    for pname, cname, y in (("VD1", "IN", 0), ("Q", "OUT", 10000)):
        ip = Port(pname, "M1", _rect("M1", 1000, y, 9000, y + 2000))
        ip.childName = cname
        xl.add(ip)
    top.add(xl)
    #- the parent's own VD1, joined to the child's IN by a real bar:
    #- ONE conductor, so any split reported is the checker's doing
    top.add(_rect("M1", 10000, 0, 50000, 2000, "VD1"))
    top.add(_rect("M1", 50000, 0, 60000, 2000, "VD1"))
    p = Port("VD1", "M1", _rect("M1", 51000, 0, 59000, 2000))
    top.ports["VD1"] = p
    top.add(p)
    top.updateBoundingRect()
    top.nodeGraphList = ["VD1"]
    return top


class InternalNetNameCollision(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Rules(_tech())
        cls.top = _name_collision()
        cls.result = cls.top.checkConnectivity()

    def test_the_childs_internal_net_is_qualified(self):
        nets = {getattr(r, "net", "")
                for r in self.top._collectPhysicalRects()}
        self.assertIn("XL/VD1", nets)
        #- the boundary net took the parent's name, so the child's own
        #- copy of it is the only VD1 left inside XL
        self.assertNotIn("VD1", {n for n in nets if n.startswith("XL")})

    def test_no_false_open(self):
        """The whole point: one label, one conductor."""
        self.assertEqual([o["net"] for o in self.result["opens"]], [])

    def test_no_false_short(self):
        self.assertEqual(self.result["shorts"], [])
