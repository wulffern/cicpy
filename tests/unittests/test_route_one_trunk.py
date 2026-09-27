"""routeOne() must honor a resolved trunk, same contract as routeVertical.

A "-|--"/"--|-" route drawn via the call shape addConnectivityRoute uses
(start=[], stop=[pin rects]) must draw its vertical run CENTRED on the
resolved trunk -- whether that came from a pin anchor (trunkright,
trunkleft, trunktab) or from the maze router's trunkx -- not at a
position derived from whichever pin rect the empty-start fallback
happens to promote.

The anchors are the interface a design should use; trunkx is the
resolved form and is tested here only because the router emits it.
"""
import os
import unittest

TECH = os.path.join(os.path.dirname(__file__), "..", "transpile",
                    "demo.tech")


class RouteOneTrunk(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from cicpy.core.rules import Rules
        Rules(TECH)

    def _route(self, options, route_type):
        from cicpy.core.rect import Rect
        from cicpy.core.route import Route
        self.pin1 = Rect("M1", 0, 0, 400, 2000)
        self.pin2 = Rect("M1", 50000, 4000, 400, 2000)
        r = Route("TESTNET", "M1", [], [self.pin1, self.pin2], options,
                  route_type)
        r.route()
        return r

    def _trunk(self, route):
        """The vertical run: the tallest rect the route drew."""
        rects = [g for g in route.children if hasattr(g, "x1")]
        return max(rects, key=lambda g: g.height())

    def test_trunkx_is_the_centreline(self):
        for rt in ("-|--", "--|-"):
            with self.subTest(route=rt):
                t = self._trunk(self._route("trunkx=25000", rt))
                self.assertEqual(t.centerX(), 25000)

    def test_trunkright_lies_on_the_pin(self):
        for rt in ("-|--", "--|-"):
            with self.subTest(route=rt):
                t = self._trunk(self._route("trunkright", rt))
                #- the rightmost trunk that still lies on every pin
                self.assertEqual(t.x2, self.pin1.x2)

    def test_trunkleft_lies_on_the_pin(self):
        for rt in ("-|--", "--|-"):
            with self.subTest(route=rt):
                t = self._trunk(self._route("trunkleft", rt))
                self.assertEqual(t.x1, self.pin2.x1)


if __name__ == "__main__":
    unittest.main()
