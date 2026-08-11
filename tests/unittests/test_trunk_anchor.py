"""A trunk said as an ANCHOR draws the wire the coordinate drew.

The plan asks for this as a round trip: search -> emit -> replay ->
assert identical. The half that can be pinned without a placement is
the emitter's own claim -- that `trunkright` names exactly the
coordinate it replaced -- and it is the half that matters, because a
half-pitch drift is a short and not a warning.

Why it is worth a test rather than an eyeball: the substitution is
made once, in the router, and consumed much later by route.py through
a different code path (`_resolveTrunkAlign`). Two implementations of
one piece of arithmetic is exactly the kind of thing that agrees on
the day it is written.
"""
import os
import unittest

TECH = os.path.join(os.path.dirname(__file__), "..", "transpile",
                    "demo.tech")


class FakeRect:
    def __init__(self, x1, y1, x2, y2, layer="M1"):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.layer = layer

    def centerX(self):
        return (self.x1 + self.x2) // 2


#- three pins of one net: two wide bars and a narrow gate tab to the
#- right of both, which is the shape every one of these columns has
BARS = [FakeRect(0, 0, 22400, 4000), FakeRect(0, 40000, 20000, 44000)]
TAB = FakeRect(30000, 20000, 33200, 24000)


class Anchors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from cicpy.core.rules import Rules
        Rules(TECH)

    def _coords(self, rects, layer="M1"):
        from cicpy.core.route import trunkAnchorCoords
        return trunkAnchorCoords(rects, layer)

    def test_anchors_lie_on_the_pins(self):
        a = self._coords(BARS)
        #- trunkright is the COMMON overlap's right edge, half a wire
        #- in, so it lands on every bar including the shorter one
        self.assertLessEqual(a["trunkright"], min(r.x2 for r in BARS))
        self.assertGreaterEqual(a["trunkleft"], max(r.x1 for r in BARS))

    def test_tab_lane_is_the_rightmost_narrow_rect(self):
        a = self._coords(BARS + [TAB])
        self.assertEqual(a["trunktab"], TAB.centerX())

    def test_emitter_substitutes_only_an_exact_anchor(self):
        from cicpy.core.mazerouter import anchored_options
        a = self._coords(BARS)
        exact = f"trunkx={a['trunkright']}"
        self.assertEqual(anchored_options(exact, BARS, "M1"), "trunkright")
        #- one unit off is a different lane and stays a coordinate:
        #- moving a wire the search placed against a map of its
        #- neighbours is how it lands on the neighbour it avoided
        off = f"trunkx={a['trunkright'] + 1}"
        self.assertEqual(anchored_options(off, BARS, "M1"), off)

    def test_substitution_keeps_the_rest_of_the_options(self):
        from cicpy.core.mazerouter import anchored_options
        a = self._coords(BARS)
        opts = f"nostartcut,trunkx={a['trunkleft']},noendcut"
        self.assertEqual(anchored_options(opts, BARS, "M1"),
                         "nostartcut,trunkleft,noendcut")

    def test_no_trunk_and_no_pins_are_left_alone(self):
        from cicpy.core.mazerouter import anchored_options
        self.assertEqual(anchored_options("offsetlowend", BARS, "M1"),
                         "offsetlowend")
        self.assertEqual(anchored_options("trunkx=17", [], "M1"),
                         "trunkx=17")

    def test_round_trip_through_route_py(self):
        """The anchor the router writes is the anchor route.py reads.

        The inverse arithmetic lives in the router and the forward
        arithmetic in Route; this asserts they are the same function,
        which is the whole basis for replacing a coordinate with a
        name.
        """
        from cicpy.core.mazerouter import anchored_options
        from cicpy.core.route import Route, trunkAnchorCoords
        rects = BARS + [TAB]
        a = self._coords(rects)
        for name in ("trunktab", "trunkright", "trunkleft"):
            written = anchored_options(f"trunkx={a[name]}", rects, "M1")
            self.assertEqual(written, name)
            r = Route.__new__(Route)
            r.startRects, r.stopRects, r.routeLayer = [], list(rects), "M1"
            self.assertEqual(int(r.trunkAnchors()[name]), int(a[name]))
        self.assertEqual(trunkAnchorCoords(rects, "M1"), a)


if __name__ == "__main__":
    unittest.main()
