"""The maze router, against the layout whose failures motivated it.

Each test here corresponds to something that actually went wrong while
routing LELOTEMP_OTAR by hand, so a regression is measured against a
real short rather than an invented one. See plans/router_plan.md.
"""
import os
import unittest

IP = os.path.join(os.path.dirname(__file__), "..", "..", "..")
CIC = os.path.join(IP, "lelo_temp_sky130a", "design",
                   "LELO_TEMP_SKY130A", "LELOTEMP_OTAR.cic")
LIB = os.path.join(IP, "rey_atr_sky130a", "design", "REY_ATR_SKY130A.cic")
TECH = os.path.join(IP, "tech_sky130A", "cic", "sky130.tech")

#- VDS's pin, and a spot in the mid channel with nothing in it
VDS_PIN = (270000, 104000)
CLEAR = (270000, 245000)


def _have_fixture():
    return all(os.path.exists(p) for p in (CIC, LIB, TECH))


@unittest.skipUnless(_have_fixture(), "LELOTEMP_OTAR fixture not present")
class MazeRouterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from cicpy.cic import load_design
        from cicpy.core.rules import Rules
        from cicpy.core.trackmap import TrackMap
        Rules(TECH)
        design = load_design(CIC, [LIB])
        cls.cell = design.cells["LELOTEMP_OTAR"]
        cls.tm = TrackMap(cls.cell, block_pins=True).build()

    def router(self, net):
        from cicpy.core.mazerouter import MazeRouter
        return MazeRouter(self.tm, net)

    #-- obstacles ---------------------------------------------------

    def test_via_refused_over_a_foreign_pin(self):
        self.assertFalse(self.router("VS").via_is_free(*VDS_PIN))

    def test_via_allowed_where_nothing_is(self):
        self.assertTrue(self.router("VS").via_is_free(*CLEAR))

    def test_pins_closer_than_a_pad_forbid_a_via_on_either(self):
        """The physical fact behind the hand-routing shorts.

        The resistor's terminals are 4000 apart and a via pad is 8800,
        so a pad centred on one covers the other. No layer change is
        possible directly on either pin -- by anyone, including the net
        that owns the pin. That is why the search must detour, and why
        no amount of track picking ever fixed it.
        """
        self.assertFalse(self.router("VDS").via_is_free(*VDS_PIN))

    def test_index_has_no_duplicates(self):
        """A pin spans many tracks; it must be indexed once."""
        r = self.router("VS")
        for bucket in r._pin_index.values():
            self.assertEqual(len(bucket), len(set(bucket)))

    #-- search ------------------------------------------------------

    def test_free_span_is_a_straight_run(self):
        r = self.router("VS")
        path = r.search((200000, 269000, "M3"), (239000, 269000, "M3"))
        self.assertEqual({n[2] for n in path}, {"M3"},
                         "a clear horizontal span should need no via")
        self.assertEqual(path[0][1], path[-1][1])

    def test_search_detours_around_a_blocked_column(self):
        """The whole point: go around, do not drive through.

        A layer change on top of VDS's pin is illegal, so the path must
        leave the pin's x-span, change layer there, and come back.
        """
        r = self.router("VS")
        path = r.search((VDS_PIN[0], VDS_PIN[1], "M3"),
                        (VDS_PIN[0], VDS_PIN[1], "M4"))
        self.assertGreater(len(path), 2, "took the illegal direct via")
        #- every layer change on the path must be at a legal column
        for x, y, _layer in path:
            pass
        changes = [(a, b) for a, b in zip(path, path[1:]) if a[2] != b[2]]
        self.assertTrue(changes, "no layer change at all")
        for a, _b in changes:
            self.assertTrue(r.via_is_free(a[0], a[1]),
                            f"changed layer at {a[:2]}, which is blocked")

    def test_bounded(self):
        """track_at returns the NEAREST track, so it answers for points
        far outside the cell too. Without a bounds check the grid is
        infinite and the search never returns -- it did not, once."""
        r = self.router("VS")
        x1, y1, x2, y2 = self.tm.extent
        self.assertFalse(r.in_bounds(x2 + 10 ** 6, y1))
        self.assertTrue(r.in_bounds((x1 + x2) // 2, (y1 + y2) // 2))

    def test_snap_puts_an_off_grid_goal_on_the_grid(self):
        """An unsnapped goal one pitch off is simply unreachable, and
        the search reports 'no path, closest approach 1000 away' --
        true, and useless."""
        r = self.router("VS")
        snapped = r.snap((240000, 269000, "M3"))
        path = r.search((200000, 269000, "M3"), (240000, 269000, "M3"))
        self.assertEqual(path[-1], snapped)

    def test_blocked_carries_a_diagnosis(self):
        """'No route' is not a diagnosis."""
        from cicpy.core.mazerouter import Blocked
        r = self.router("VS")
        x1, y1, x2, y2 = self.tm.extent
        with self.assertRaises(Blocked) as cm:
            #- a goal outside the extent can never be reached
            r.search((200000, 269000, "M3"), (x2 + 10 ** 6, 269000, "M3"))
        self.assertGreater(cm.exception.reached, 0)


if __name__ == "__main__":
    unittest.main()
