"""NETS: what a net's NAME says about how it should be routed.

ROUTE.costs and ROUTE.directions are per LAYER and never see the net,
so a technology had no way to say "the bias currents are sensitive" or
"the supplies carry real current". These tests pin the three things the
table decides: the price of a net's steps, the width a searched route is
drawn at, and the penalty for running alongside a sensitive net.

Everything runs against the in-repo fixture (tests/transpile), so
nothing here depends on a sibling checkout.
"""
import os
import unittest

try:
    from . import fixture
except ImportError:          #- discover runs this file as a top-level module
    import fixture


@unittest.skipUnless(fixture.have(), "fixture not present")
class NetRuleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cell, cls.tm = fixture.load()

    #-- classification -------------------------------------------------

    def test_first_match_wins_so_a_supply_is_not_digital(self):
        """VDD_1V8 matches BOTH ^VDD and _1V8$, and the order decides.

        This is the whole reason the table is a list. A dict would have
        made the answer depend on insertion order, which is not
        something a technology file should have to know.
        """
        self.assertEqual(self.tm.net_class("VDD_1V8"), "supply")
        self.assertEqual(self.tm.net_class("PWRUP_1V8"), "digital")

    def test_a_net_no_rule_matches_has_no_class(self):
        self.assertEqual(self.tm.net_class("VBN1"), "")
        self.assertEqual(self.tm.net_rule("VBN1"), {})
        self.assertEqual(self.tm.keepaway_tracks("VBN1"), 0)

    def test_bias_currents_are_sensitive(self):
        for net in ("IBP_1U", "IBN", "IBP_1U<3>"):
            self.assertEqual(self.tm.net_class(net), "sensitive", net)
            self.assertEqual(self.tm.keepaway_tracks(net), 2, net)

    def test_an_unparsable_pattern_is_ignored_not_fatal(self):
        """A typo in the technology must not take the router down."""
        tm = self.tm
        saved = getattr(tm, "_net_rules", None)
        try:
            tm._net_rules = None
            del tm._net_rules
            import re as _re
            #- inject a bad entry the way the tech would
            orig = tm.rules.getValue

            def patched(a, b):
                if b == "NETS":
                    return [{"match": "^(unclosed", "class": "bad"},
                            {"match": "^VDD", "class": "supply"}]
                return orig(a, b)
            tm.rules.getValue = patched
            tm._net_rule_cache = {}
            self.assertEqual(tm.net_class("VDD_1V8"), "supply")
        finally:
            tm.rules.getValue = orig
            tm._net_rules = saved
            tm._net_rule_cache = {}

    #-- cost -----------------------------------------------------------

    def test_layer_cost_without_a_net_is_the_layer_price(self):
        """The old one-argument call must mean exactly what it did."""
        for layer in ("M1", "M2", "M3"):
            self.assertEqual(self.tm.layer_cost(layer),
                             self.tm.layer_cost(layer, None), layer)

    def test_a_nets_rule_scales_its_own_steps(self):
        """demo.tech prices the digital class at 2x."""
        base = self.tm.layer_cost("M2")
        self.assertEqual(self.tm.layer_cost("M2", "PWRUP_1V8"), base * 2)
        #- and a net with no cost in its rule pays the layer price
        self.assertEqual(self.tm.layer_cost("M2", "VBN1"), base)
        self.assertEqual(self.tm.layer_cost("M2", "IBP_1U"), base)

    def test_cost_never_falls_below_one(self):
        """A zero-cost step would make the search free and unbounded."""
        tm = self.tm
        orig = tm.net_rule
        try:
            tm.net_rule = lambda net: {"cost": 0}
            self.assertGreaterEqual(tm.layer_cost("M2", "anything"), 1)
        finally:
            tm.net_rule = orig

    #-- width ----------------------------------------------------------

    def test_a_supply_is_drawn_wider_than_the_technology_minimum(self):
        from cicpy.core.mazerouter import MazeRouter
        plain = MazeRouter(self.tm, "VBN1")
        supply = MazeRouter(self.tm, "VSS")
        self.assertEqual(plain.net_width("M2"), plain.rule("M2", "width"))
        self.assertEqual(supply.net_width("M2"),
                         3 * supply.rule("M2", "width"))

    def test_a_wide_net_reserves_the_room_it_occupies(self):
        """The search must keep foreign wires away from the WIDE wire.

        Reserving the technology minimum and then drawing three times
        it puts the metal straight over the neighbouring track -- which
        DRC sees and, if the neighbour is another net, LVS does.
        """
        from cicpy.core.mazerouter import MazeRouter
        plain = MazeRouter(self.tm, "VBN1")
        supply = MazeRouter(self.tm, "VSS")
        self.assertGreater(supply.clearance("M2"), plain.clearance("M2"))
        self.assertEqual(supply.clearance("M2"),
                         supply.net_width("M2") + supply.rule("M2", "space"))

    #-- keepaway -------------------------------------------------------

    def test_keepaway_is_a_penalty_and_never_an_exclusion(self):
        """is_free must not change; only the price does.

        A hard exclusion turns a crowded column into "no path", and an
        unroutable net is a worse answer than a net that took the long
        way round.
        """
        from cicpy.core.mazerouter import MazeRouter
        r = MazeRouter(self.tm, "VBN1")
        layer = "M2"
        tracks = self.tm.tracks.get(layer) or []
        if not tracks:
            self.skipTest("fixture has no M2 tracks")
        #- whatever the penalty says, the freedom answer is unchanged
        for t in tracks[:40]:
            lo, hi = int(self.cell.y1), int(self.cell.y1) + 1000
            before = r.is_free(layer, int(t.coord), lo, hi)
            r.keepaway_penalty(layer, int(t.coord), lo, hi)
            self.assertEqual(before, r.is_free(layer, int(t.coord), lo, hi))

    def test_no_penalty_when_the_technology_declares_no_sensitive_net(self):
        from cicpy.core.mazerouter import MazeRouter
        tm = self.tm
        r = MazeRouter(tm, "VBN1")
        saved = getattr(tm, "_has_keepaway", None)
        try:
            tm._has_keepaway = False
            self.assertEqual(r.keepaway_penalty("M2", 0, 0, 1000), 0)
        finally:
            tm._has_keepaway = saved

    def test_a_step_beside_a_sensitive_net_costs_more_than_one_away(self):
        """The point of the whole feature, measured on the fixture.

        A synthetic sensitive net is occupied on one track; a step on
        the adjacent track must cost more than a step several tracks
        out, and both must cost more than one nowhere near it.
        """
        from cicpy.core.mazerouter import MazeRouter
        layer = "M2"
        tracks = self.tm.tracks.get(layer) or []
        if len(tracks) < 12:
            self.skipTest("fixture has too few M2 tracks")
        lo, hi = int(self.cell.y1) + 2000, int(self.cell.y1) + 8000
        victim = tracks[len(tracks) // 2]
        victim.occupy("IBP_TESTNET", lo, hi)
        try:
            r = MazeRouter(self.tm, "VBN1")
            pitch = self.tm.vpitch if self.tm.directions.get(layer) == "v" \
                else self.tm.hpitch
            here = r.keepaway_penalty(layer, int(victim.coord), lo, hi)
            one = r.keepaway_penalty(layer, int(victim.coord) + pitch, lo, hi)
            far = r.keepaway_penalty(layer, int(victim.coord) + 9 * pitch,
                                     lo, hi)
            self.assertGreater(here, one)
            self.assertGreater(one, 0)
            self.assertEqual(far, 0)
        finally:
            victim.wires.pop("IBP_TESTNET", None)
            victim.spans.pop("IBP_TESTNET", None)

    def test_a_sensitive_net_does_not_keep_away_from_itself(self):
        from cicpy.core.mazerouter import MazeRouter
        layer = "M2"
        tracks = self.tm.tracks.get(layer) or []
        if len(tracks) < 12:
            self.skipTest("fixture has too few M2 tracks")
        lo, hi = int(self.cell.y1) + 2000, int(self.cell.y1) + 8000
        victim = tracks[len(tracks) // 2]
        victim.occupy("IBP_TESTNET", lo, hi)
        try:
            r = MazeRouter(self.tm, "IBP_TESTNET")
            self.assertEqual(
                r.keepaway_penalty(layer, int(victim.coord), lo, hi), 0)
        finally:
            victim.wires.pop("IBP_TESTNET", None)
            victim.spans.pop("IBP_TESTNET", None)

    def test_unattributed_metal_does_not_trigger_a_penalty(self):
        """"?" is a device's internal rail, not a net with an opinion."""
        from cicpy.core.mazerouter import MazeRouter
        layer = "M2"
        tracks = self.tm.tracks.get(layer) or []
        if len(tracks) < 12:
            self.skipTest("fixture has too few M2 tracks")
        lo, hi = int(self.cell.y1) + 2000, int(self.cell.y1) + 8000
        t = tracks[len(tracks) // 3]
        t.occupy("?", lo, hi)
        try:
            r = MazeRouter(self.tm, "IBP_1U")
            self.assertEqual(r.keepaway_penalty(layer, int(t.coord), lo, hi),
                             0)
        finally:
            t.wires.pop("?", None)
            t.spans.pop("?", None)


if __name__ == "__main__":
    unittest.main()
