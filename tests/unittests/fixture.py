"""The in-repo fixture the router and track-map tests run against.

NO LINKS OUT OF THIS REPOSITORY. These tests used to load
LELOTEMP_OTAR from lelo_temp_sky130a, a library from rey_atr_sky130a
and a technology from tech_sky130A -- three sibling checkouts that CI
does not have, so every one of them SKIPPED there and the suite was
green while testing nothing. Worse, they carried hand-written
coordinates into another repository's layout: when that layout was
republished the frame shifted, the coordinates fell off the pin they
named, and three tests failed as if the router had regressed.

cicpy's own `tests/transpile` fixture answers the same questions:
SAR9B_CV.cic.gz is a real placed design and demo.tech is a real
technology. Everything below is DERIVED from them, so nothing here
can go stale in the way the old literals did.
"""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CIC = os.path.join(HERE, "..", "transpile", "SAR9B_CV.cic.gz")
TECH = os.path.join(HERE, "..", "transpile", "demo.tech")
CELL = "ALGIC001_SAR9B_CV"


def have():
    return all(os.path.exists(p) for p in (CIC, TECH))


def load():
    """(cell, trackmap) for the fixture cell, technology loaded."""
    from cicpy.cic import load_design
    from cicpy.core.rules import Rules
    from cicpy.core.trackmap import TrackMap
    Rules(TECH)
    design = load_design(CIC, [])
    cell = design.cells[CELL]
    return cell, TrackMap(cell, block_pins=True).build()


def a_pin(cell, tm, skip=()):
    """(net, (x, y)) for a net with a pin on the pin layer.

    The lowest pin of the first net that has one, and its centre: a
    probe point has to be ON the pin for "your own pin" to mean
    anything, which is exactly what the old literals stopped being.
    """
    for net in (getattr(cell, "nodeGraphList", []) or []):
        if net in skip:
            continue
        g = cell.nodeGraph.get(net)
        rects = [p.get(tm.pin_layer) for p in getattr(g, "ports", [])
                 if hasattr(p, "get") and p.get(tm.pin_layer) is not None]
        if not rects:
            continue
        #- the one nearest the middle of the cell: a pin jammed
        #- against an edge has no room to detour AROUND, and the
        #- detour is what several of these tests are about.
        cx = (int(cell.x1) + int(cell.x2)) // 2
        cy = (int(cell.y1) + int(cell.y2)) // 2
        r = min(rects, key=lambda r: (abs((int(r.x1) + int(r.x2)) // 2 - cx)
                                      + abs((int(r.y1) + int(r.y2)) // 2 - cy)))
        return net, ((int(r.x1) + int(r.x2)) // 2,
                     (int(r.y1) + int(r.y2)) // 2)
    raise unittest.SkipTest(f"no pin on {tm.pin_layer} in the fixture")


def a_clear_point(cell, tm, net):
    """A point inside the cell where `net` may drop a via.

    Derived, for the same reason the pin is: "somewhere empty" is a
    property of the layout, and writing one down is how the old fixture
    came to name a spot that was no longer empty.
    """
    from cicpy.core.mazerouter import MazeRouter
    r = MazeRouter(tm, net)
    xs = [t.coord for t in tm.tracks.get("M2", [])]
    ys = [t.coord for t in tm.tracks.get("M3", [])]
    for y in ys[len(ys) // 2:]:
        for x in xs:
            #- asked exactly as the caller will ask it: with the
            #- router's own default layers, not a pair chosen here
            if r.via_is_free(int(x), int(y)):
                return (int(x), int(y))
    raise unittest.SkipTest("no clear via column in the fixture")


def a_clear_span(cell, tm, net):
    """Two points on one horizontal track with nothing between them.

    The router tests need "a free run" to assert about; which run it is
    does not matter, and naming one in another repository's layout is
    how the old fixture broke.
    """
    from cicpy.core.mazerouter import MazeRouter
    r = MazeRouter(tm, net)
    xs = [int(t.coord) for t in tm.tracks.get("M2", [])]
    if len(xs) < 4:
        raise unittest.SkipTest("fixture has too few vertical tracks")
    lo, hi = xs[1], xs[-2]
    for t in tm.tracks.get("M3", []):
        y = int(t.coord)
        if r.is_free("M3", y, lo, hi):
            return (lo, y), (hi, y)
    raise unittest.SkipTest("no clear M3 span in the fixture")
