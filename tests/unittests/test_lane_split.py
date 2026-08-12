"""How many rails a net's pins need, and which pins each one serves.

A straight vertical needs one column every pin shares. When they share
none the net is not unroutable -- it is not ONE RAIL, and the designs
have been saying so by hand: "VD1 mixes two pin shapes the stack router
declines: the wide D bars and the right-lane gate tabs. No single
vertical lands on all of them, so two do."

The piercing is greedy, which is optimal on intervals, and the property
that matters for connectivity is the last test here: a pin wide enough
to hold two lanes ends up in BOTH groups, and it is that shared pin
whose own metal joins the rails. Without it two rails are two nets.
"""
import unittest

from cicpy.core.mazerouter import lanes_over_pins


class FakeRect:
    def __init__(self, x1, x2, name=""):
        self.x1, self.x2 = x1, x2
        self.y1, self.y2 = 0, 4000
        self.instName = name


W2 = 1500


class LaneSplit(unittest.TestCase):

    def test_one_lane_when_the_pins_share_a_column(self):
        pins = [FakeRect(0, 20000), FakeRect(0, 22400), FakeRect(1000, 20000)]
        lanes = lanes_over_pins(pins, W2)
        self.assertEqual(len(lanes), 1)
        self.assertEqual(len(lanes[0][1]), 3)

    def test_two_lanes_for_bars_and_a_tab(self):
        """The shape every one of these columns has: wide drain bars
        and a gate tab off to the right, sharing nothing."""
        bars = [FakeRect(0, 22400, "xnd1"), FakeRect(0, 20000, "xns1")]
        tab = FakeRect(30000, 33200, "xnd3")
        lanes = lanes_over_pins(bars + [tab], W2)
        self.assertEqual(len(lanes), 2)
        served = [set(r.instName for r in g) for _, g in lanes]
        self.assertIn({"xnd1", "xns1"}, served)
        self.assertIn({"xnd3"}, served)

    def test_every_lane_lies_on_every_pin_it_claims(self):
        pins = [FakeRect(0, 22400), FakeRect(30000, 33200),
                FakeRect(10000, 31000)]
        for lane, group in lanes_over_pins(pins, W2):
            for r in group:
                self.assertLessEqual(r.x1 + W2, lane)
                self.assertLessEqual(lane, r.x2 - W2)

    def test_every_pin_is_served(self):
        pins = [FakeRect(0, 22400), FakeRect(30000, 33200),
                FakeRect(50000, 53200), FakeRect(10000, 31000)]
        lanes = lanes_over_pins(pins, W2)
        served = {id(r) for _, g in lanes for r in g}
        self.assertEqual(served, {id(r) for r in pins})

    def test_a_pin_too_narrow_for_the_wire_gives_up(self):
        self.assertEqual(lanes_over_pins([FakeRect(0, 1000)], W2), [])

    def test_a_wide_pin_joins_the_rails_it_spans(self):
        """The whole basis for not drawing a wire between the rails.

        The bars run 0..22400 and the tab 20000..23200; a pin spanning
        both lanes is in both groups, and its own metal is the join.
        """
        wide = FakeRect(0, 23200, "xnd1")
        bar = FakeRect(0, 20000, "xns1")
        tab = FakeRect(20000, 23200, "xnd3")
        lanes = lanes_over_pins([wide, bar, tab], W2)
        self.assertEqual(len(lanes), 2)
        shared = [r for r in (wide, bar, tab)
                  if sum(1 for _, g in lanes if r in g) > 1]
        self.assertIn(wide, shared)


if __name__ == "__main__":
    unittest.main()
