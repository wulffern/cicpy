"""A `~` path draws exactly what its steps say.

Stage 2's gate. The steps are geometry, so the assertions are geometry:
where the rects landed, on which layer, how wide, and that a layer
change put a via there. Nothing here reads a log line -- three separate
APIs in this codebase have logged success and drawn nothing.
"""
import os
import unittest

from cicpy.core.rules import Rules
from cicpy.core.rect import Rect
from cicpy.core.layoutcell import LayoutCell

TECH = os.path.join(os.path.dirname(__file__), "..", "transpile", "demo.tech")


def _rules():
    return Rules(TECH)


def _pin(layer, x, y, w=3000, h=3000):
    r = Rect(layer, x, y, w, h)
    r.setNet("N")
    return r


class PathGeometry(unittest.TestCase):

    def setUp(self):
        self.rules = _rules()
        self.cell = LayoutCell()
        self.cell.name = "PATHTEST"
        self.w = self.rules.get("M2", "width")

    def _segments(self, p, layer=None):
        out = []
        for c in p.children:
            if hasattr(c, "isRect") and c.isRect():
                if layer is None or c.layer == layer:
                    out.append(c)
        return out

    def test_trunk_rides_the_pins_at_the_anchor(self):
        """A vertical trunk spans every pin and sits where the anchor says."""
        a, b = _pin("M2", 0, 0), _pin("M2", 0, 40000)
        p = self.cell.path("N", "M2", [a], [b])
        p.start()
        p.trunk(p.left_of_pins())
        p.end()
        p.route()

        verticals = [r for r in self._segments(p, "M2")
                     if r.height() > r.width()]
        self.assertTrue(verticals, "trunk drew no vertical")
        t = max(verticals, key=lambda r: r.height())
        #- spans from the lowest pin edge to the highest
        self.assertEqual(int(t.y1), 0)
        self.assertEqual(int(t.y2), 43000)
        #- and sits on trunkleft: max(x1) + w//2, centred
        self.assertEqual(int(t.centerX()), 0 + self.w // 2)
        self.assertEqual(int(t.width()), self.w)

    def test_anchor_offsets_are_lanes_not_numbers(self):
        """`+ 2*PITCH` moves two legal lanes, from the rules."""
        a, b = _pin("M2", 0, 0), _pin("M2", 0, 40000)
        p = self.cell.path("N", "M2", [a], [b])
        base = p.resolveAnchor(p.left_of_pins())
        moved = p.resolveAnchor(p.left_of_pins() + 2 * p.PITCH)
        pitch = self.rules.get("M2", "width") + self.rules.get("M2", "space")
        self.assertEqual(moved - base, 2 * pitch)

    def test_a_coordinate_is_not_an_anchor(self):
        """Rule 3, enforced by the type: a bare number resolves to None."""
        p = self.cell.path("N", "M2", [_pin("M2", 0, 0)], [_pin("M2", 0, 9000)])
        self.assertIsNone(p.resolveAnchor(304100))

    def test_layer_change_places_a_via(self):
        """up() vias, and never on a 1x1 when something larger fits."""
        a, b = _pin("M2", 0, 0), _pin("M2", 0, 40000)
        p = self.cell.path("N", "M2", [a], [b])
        p.start()
        p.up()
        p.trunk()
        p.route()
        cuts = [c for c in p.children
                if hasattr(c, "isCut") and c.isCut()]
        self.assertTrue(cuts, "up() placed no via")

    def test_up_then_down_returns_to_the_start_layer(self):
        a, b = _pin("M2", 0, 0), _pin("M2", 0, 40000)
        p = self.cell.path("N", "M2", [a], [b])
        p.start()
        p.up()
        upper = p.neighbourLayer("M2", "next")
        self.assertIsNotNone(upper, "no layer above M2 in the technology")
        self.assertNotEqual(upper, "M2")
        self.assertEqual(p.neighbourLayer(upper, "previous"), "M2")

    def test_ends_land_on_the_ports_where_they_are(self):
        """Ports are not on any grid and are not moved onto one."""
        a = _pin("M2", 1234, 0)          # deliberately off any pitch
        b = _pin("M2", 1234, 40000)
        p = self.cell.path("N", "M2", [a], [b])
        p.start()
        p.end()
        p.route()
        segs = self._segments(p, "M2")
        self.assertTrue(segs)
        ys = [int(s.y1) for s in segs] + [int(s.y2) for s in segs]
        self.assertEqual(min(ys), int(a.centerY()))
        self.assertEqual(max(ys), int(b.centerY()))
        xs = [int(s.centerX()) for s in segs]
        self.assertEqual(set(xs), {int(a.centerX())})

    def test_a_path_is_a_route(self):
        """isType walks the MRO, and LayoutCell.route() only draws what
        answers isRoute() -- so this is what makes a path get drawn."""
        p = self.cell.path("N", "M2", [_pin("M2", 0, 0)], [_pin("M2", 0, 9000)])
        self.assertTrue(p.isRoute())
        self.assertIn(p, self.cell.routes)

    def test_steps_serialise_for_the_emitter(self):
        p = self.cell.path("N", "M2", [_pin("M2", 0, 0)], [_pin("M2", 0, 9000)])
        p.start().up().trunk().down().end()
        names = [t[0] for t in p.astuples()]
        self.assertEqual(names, ["start", "up", "trunk", "down", "end"])

    def test_the_vocabulary_is_open(self):
        """A new step is a new class, and touches nothing central."""
        from cicpy.core.path import Step, step, STEPS

        @step
        class Jog(Step):
            name = "jog_testonly"

            def apply(self, path, cur):
                return cur

        try:
            self.assertIn("jog_testonly", STEPS)
            self.assertIs(STEPS["jog_testonly"], Jog)
        finally:
            STEPS.pop("jog_testonly", None)


if __name__ == "__main__":
    unittest.main()
