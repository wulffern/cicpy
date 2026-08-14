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

#- VDS's pin, and a spot in the mid channel with nothing in it.
#-
#- DERIVED, NOT WRITTEN DOWN. These were literals and they rotted: the
#- publish frame shifts whenever flat content changes, so the y drifted
#- out of the pin (92000, against a pin at 105000..109000) and three
#- tests then asserted things about a point that is on no pin at all --
#- which reads as a router regression and is a fixture one.
#-
#- THE FIXTURE ITSELF IS STILL IN ANOTHER REPOSITORY, which is wrong
#- and is why these skip in CI. tests/unittests/fixture.py is the
#- in-repo replacement (SAR9B_CV.cic.gz + demo.tech, which carries
#- routing directions now); moving these tests onto it is not a
#- repoint, because several of them need a particular SHAPE -- a
#- foreign pin whose column is blocked but which can be routed around
#- -- and that has to be found in the new design, not assumed.
VDS_PIN = None
CLEAR = None


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
        global VDS_PIN, CLEAR
        g = cls.cell.nodeGraph.get("VDS")
        rects = [p.get("M1") for p in getattr(g, "ports", [])
                 if hasattr(p, "get") and p.get("M1") is not None]
        if not rects:
            raise unittest.SkipTest("fixture has no VDS pin on M1")
        r = min(rects, key=lambda r: int(r.y1))
        VDS_PIN = ((int(r.x1) + int(r.x2)) // 2,
                   (int(r.y1) + int(r.y2)) // 2)
        CLEAR = (VDS_PIN[0], int(cls.cell.y2) - 40000)

    def router(self, net):
        from cicpy.core.mazerouter import MazeRouter
        return MazeRouter(self.tm, net)

    #-- obstacles ---------------------------------------------------

    def test_via_refused_over_a_foreign_pin(self):
        self.assertFalse(self.router("VS").via_is_free(*VDS_PIN))

    def test_via_allowed_where_nothing_is(self):
        self.assertTrue(self.router("VS").via_is_free(*CLEAR))

    def test_via_size_comes_from_the_technology(self):
        """Not from a constant, and this test exists because of one.

        An earlier version hard coded an 8800 pad, taken from a note
        about pad clashes, and asserted here that no layer change was
        possible on either resistor terminal because they sit 4000 apart.
        That was the constant talking, not the layout: the real 1x1 cut
        is 4000 square, so a via centred on one terminal reaches 2000 and
        the neighbour at 4000 is clear. Asking Cut for the size fixed it,
        and unblocked all five ladder nets that the wrong constant had
        declared unroutable.
        """
        r = self.router("VDS")
        self.assertEqual(r.via_extent("M1", "M2"), (4000, 4000))

    def test_a_via_on_the_pin_layer_needs_to_know_its_own_pin(self):
        """The contract, third edition.

        First: tolerate everything unattributed on M1 (shorted through
        device rails). Second: refuse unless told which rect is your
        own (this test's old first assertion). Third, now that instance
        geometry is ATTRIBUTED: the metal at a pin is KNOWN to be the
        pin's net, so a via on your own pin is allowed whether or not
        anyone told you -- and a via on another net's pin refuses,
        which is the half that was always the point.
        """
        r = self.router("VDS")
        #- its own pin, and the map knows it: allowed
        self.assertTrue(r.via_is_free(VDS_PIN[0], VDS_PIN[1], "M1", "M2"))
        #- the same spot for another net: refused
        self.assertFalse(
            self.router("VS").via_is_free(VDS_PIN[0], VDS_PIN[1],
                                          "M1", "M2"))
        #- told that this pin is its own: allowed
        g = self.cell.nodeGraph.get("VDS")
        own = [p.get("M1") for p in g.ports
               if hasattr(p, "get") and p.get("M1") is not None]
        #- overlapping the via BOX, not containing the centre: the probe
        #- point is a track coordinate and need not sit inside the rect
        w, h = r.via_extent("M1", "M2")
        bx1, bx2 = VDS_PIN[0] - w // 2, VDS_PIN[0] + w // 2
        by1, by2 = VDS_PIN[1] - h // 2, VDS_PIN[1] + h // 2
        own = [x for x in own
               if not (bx2 <= x.x1 or bx1 >= x.x2)
               and not (by2 <= x.y1 or by1 >= x.y2)]
        self.assertTrue(own, "fixture has no VDS pin near the probe point")
        r._own = own
        self.assertTrue(r.via_is_free(VDS_PIN[0], VDS_PIN[1], "M1", "M2"))

    def test_a_via_only_occupies_the_layers_it_connects(self):
        """M1->M2 under an unrelated M4 wire is not a short.

        The via column model was right about a whole descent and wrong
        about one step. Scanning every layer made an M1->M2 via illegal
        beneath VS's M4 trunk, which blocked all five ladder nets at
        their own pins.
        """
        r = self.router("net1")
        self.assertEqual(sorted(r._via_layers("M1", "M2")), ["M1", "M2"])
        self.assertNotIn("M4", r._via_layers("M1", "M2"))

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
        for a, b in changes:
            self.assertTrue(r.via_is_free(a[0], a[1], a[2], b[2]),
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

    #-- path to geometry --------------------------------------------

    def test_straight_path_collapses_to_one_run(self):
        """A path is per-track; geometry should not be."""
        r = self.router("VS")
        path = r.search((200000, 269000, "M3"), (239000, 269000, "M3"))
        runs, vias = r.segments(path)
        self.assertEqual(len(runs), 1, "14 nodes should be one rect")
        self.assertEqual(vias, [])

    def test_detour_segments_into_runs_and_vias(self):
        r = self.router("VS")
        path = r.search((VDS_PIN[0], VDS_PIN[1], "M3"),
                        (VDS_PIN[0], VDS_PIN[1], "M4"))
        runs, vias = r.segments(path)
        self.assertGreater(len(runs), 1)
        self.assertEqual(len(vias), len(runs) - 1,
                         "one via per layer change")

    def test_every_emitted_via_is_at_a_legal_column(self):
        """The property that matters. If this fails the router has
        drawn the short it was built to avoid."""
        r = self.router("VS")
        path = r.search((VDS_PIN[0], VDS_PIN[1], "M3"),
                        (VDS_PIN[0], VDS_PIN[1], "M4"))
        _runs, vias = r.segments(path)
        for la, lb, x, y in vias:
            #- with the via's OWN layers: the check is layer specific,
            #- and asking about a different pair asks a different
            #- question
            self.assertTrue(r.via_is_free(x, y, la, lb),
                            f"via {la}->{lb} at {(x, y)} is not legal")

    def test_search_does_not_mutate(self):
        """Searching must be free of side effects, so a path can be
        inspected and asserted on before anything is drawn."""
        r = self.router("VS")
        before = len(self.cell.children)
        r.search((200000, 269000, "M3"), (239000, 269000, "M3"))
        self.assertEqual(len(self.cell.children), before)

    def test_emit_makes_real_cut_instances(self):
        """Vias must be InstanceCut, not copies.

        Cut.getInstance already returns a fresh InstanceCut per call and
        registers the cut cell for Design.addCuts() to hoist. Taking a
        getCopy() of it produced something the printer did not recognise
        as an instance: the wires appeared in the .mag and not one via
        did, so the routed net stayed open with nothing to show why.
        """
        from cicpy.core.instancecut import InstanceCut
        r = self.router("VS")
        path = r.search((VDS_PIN[0], VDS_PIN[1], "M3"),
                        (VDS_PIN[0], VDS_PIN[1], "M4"))
        before = len(self.cell.children)
        nrect, ncut = r.emit(self.cell, path)
        added = self.cell.children[before:]
        try:
            self.assertGreater(ncut, 0)
            cuts = [c for c in added if isinstance(c, InstanceCut)]
            self.assertEqual(len(cuts), ncut,
                             "emitted vias are not InstanceCut")
        finally:
            del self.cell.children[before:]

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
