"""A `~` story must survive a round trip through the .cic.

It did not: the writer emitted class "Path" and the reader had no case
for it, so a story was dropped on read ("Unkown class Path") and every
tool working from the .cic saw the metal without the reasoning -- or,
before that, not even the metal.
"""
import os
import unittest

from cicpy.core.path import Path, Anchor, _TrackAnchor, _PinAnchor
from cicpy.core.rules import Rules
from cicpy.core.design import Design

#- cicpy's OWN technology, not a sibling checkout's. This reached for
#- tech_sky130A, which CI does not have, so setUpClass raised
#- FileNotFoundError and the whole class ERRORED there -- a red build
#- for a missing neighbour rather than anything about a Path.
#- Nothing here is sky130-specific: the test is that a story survives
#- a round trip, and any technology answers that.
TECH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "transpile", "demo.tech")


class TestPathJson(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        #- Cell.toJson reaches for the technology; the story under test
        #- carries none of its own
        Rules(TECH)

    def _read(self, o):
        #- the reader sets `design` before calling fromJson, and
        #- Cell.fromJson takes its prefix from it
        p = Path("", "")
        p.design = Design()
        return p.fromJson(o)

    def _story(self):
        p = Path("LPI", "M3")
        p.start()
        p.up()
        p.movex(p.track("bias", 155))
        p.movey(p.landing("y"))
        p.down()
        p.end()
        return p

    def test_steps_survive(self):
        o = self._story().toJson()
        self.assertEqual(o["class"], "Path")
        back = self._read(o)
        self.assertEqual(len(back.steps), 6)
        self.assertEqual([s.name for s in back.steps],
                         ["start", "up", "movex", "movey", "down", "end"])

    def test_anchors_survive(self):
        back = self._read(self._story().toJson())
        mx = back.steps[2]
        self.assertIsInstance(mx.anchor, _TrackAnchor)
        self.assertEqual(mx.anchor.channel, "bias")
        self.assertEqual(mx.anchor.index, 155)
        self.assertEqual(back.steps[3].anchor.axis, "y")

    def test_net_and_layer_survive(self):
        back = self._read(self._story().toJson())
        self.assertEqual(back.net, "LPI")
        self.assertEqual(back.routeLayer, "M3")
        self.assertEqual(back.routeType, "POLYLINE")

    def test_a_declared_story_carries_no_coordinate(self):
        back = self._read(self._story().toJson())
        self.assertFalse(back.isResolved())

    def test_every_registered_step_can_be_rebuilt(self):
        """A reader dies on the first step that cannot be made.

        `_LayerTo` took a required argument while the base `_make`
        called `cls()`, so a file holding a `layer` step raised
        TypeError halfway through reading a cell -- which is a broken
        design, not a warning.
        """
        from cicpy.core.path import STEPS
        for name, cls in STEPS.items():
            with self.subTest(step=name):
                st = cls._make({})
                self.assertEqual(st.toJson()["step"], name)

    def test_anchor_round_trip_is_by_kind(self):
        a = _PinAnchor("x1", "VSS", "y")
        b = Anchor.fromJson(a.toJson())
        self.assertIsInstance(b, _PinAnchor)
        self.assertEqual((b.instance, b.terminal, b.axis), ("x1", "VSS", "y"))


if __name__ == "__main__":
    unittest.main()
