"""routeOne() must honor an absolute trunkx, same contract as routeVertical.

Reproduces the gap directly: a "-|--"/"--|-" route drawn via the same
call shape addConnectivityRoute uses (start=[], stop=[pin rects]) must
draw its vertical run at the requested trunkx, not at a position derived
from whichever pin rect the empty-start fallback happens to promote.
mazerouter.py's route_spec() computes trunkx from its own obstacle-aware
search specifically for this route type -- silently discarding it here
reintroduces the trunk-collision failure the search was built to avoid.
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

    def _drawn_x_span(self, route):
        route.route()
        xs = [g.x1 for g in route.children if hasattr(g, "x1")]
        return xs

    def test_left_route_honors_absolute_trunk(self):
        from cicpy.core.rect import Rect
        from cicpy.core.route import Route
        pin1 = Rect("M1", 0, 0, 400, 2000)
        pin2 = Rect("M1", 50000, 0, 400, 2000)
        trunk = 25000
        r = Route("TESTNET", "M1", [], [pin1, pin2], f"trunkx={trunk}", "-|--")
        self.assertTrue(r.hasAbsoluteTrunk)
        self.assertEqual(r.absoluteTrunk, trunk)
        xs = self._drawn_x_span(r)
        #- the vertical run must include the requested trunk column
        self.assertTrue(any(abs(x - trunk) < 100 for x in xs),
                         f"drawn geometry at {xs} does not include "
                         f"requested trunkx={trunk}")

    def test_right_route_honors_absolute_trunk(self):
        from cicpy.core.rect import Rect
        from cicpy.core.route import Route
        pin1 = Rect("M1", 0, 0, 400, 2000)
        pin2 = Rect("M1", 50000, 0, 400, 2000)
        trunk = 25000
        r = Route("TESTNET", "M1", [], [pin1, pin2], f"trunkx={trunk}", "--|-")
        xs = self._drawn_x_span(r)
        self.assertTrue(any(abs(x - trunk) < 100 for x in xs),
                         f"drawn geometry at {xs} does not include "
                         f"requested trunkx={trunk}")


if __name__ == "__main__":
    unittest.main()
