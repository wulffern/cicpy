"""Edge pins that have a neighbour a lane away.

Two things a parent needs when two of a block's pins stand side by side
on one edge and both rise on the same layer (REY_PLL_DIVN: CK_FB on M5
beside the CKO0 tap, which the top promotes on M5):

- `addPortOnEdge(..., "narrowpin")`: the edge pin is one wire of the
  edge's layer across, not a copy of a port drawn wide for the cell's
  own hops;
- `promoteInstancePort(..., jog=(<the pin's own layer>, x))`: the pin
  steps aside on the metal it is already on, with no cut.
"""
import os
import unittest

TECH = os.path.join(os.path.dirname(__file__), "..", "transpile",
                    "demo.tech")


class EdgePins(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from cicpy.core.rules import Rules
        Rules(TECH)

    def _cell(self):
        from cicpy.core.layoutcell import LayoutCell
        from cicpy.core.rect import Rect
        from cicpy.core.rules import Rules
        self.w = int(Rules.getInstance().get("M4", "width"))
        c = LayoutCell()
        c.name = "EDGE"
        #- something to give the cell a size: the edge is its top
        c.add(Rect("M1", 0, 0, 40 * self.w, 40 * self.w))
        c.updateBoundingRect()
        return c

    def _port(self, c, wide):
        from cicpy.core.port import Port
        from cicpy.core.rect import Rect
        r = Rect("M1", 10 * self.w, 4 * self.w, wide, self.w)
        c.add(r)
        p = Port("A", "M1", r)
        c.ports["A"] = p
        return r

    def test_narrowpin_is_one_wire_across(self):
        c = self._cell()
        r = self._port(c, 3 * self.w)
        centre = int(r.centerX())
        c.addPortOnEdge("M4", "A", "top", "||", "narrowpin")
        rp = c.ports["A"].get()
        self.assertEqual(int(rp.x2 - rp.x1), self.w)
        self.assertEqual(int(rp.centerX()), centre)
        self.assertEqual(int(rp.y2), int(c.y2))

    def test_without_it_the_pin_is_the_ports_copy(self):
        c = self._cell()
        self._port(c, 3 * self.w)
        c.addPortOnEdge("M4", "A", "top", "||", "")
        rp = c.ports["A"].get()
        self.assertEqual(int(rp.x2 - rp.x1), 3 * self.w)

    def test_a_pin_already_narrow_is_left(self):
        c = self._cell()
        self._port(c, self.w // 2)
        c.addPortOnEdge("M4", "A", "top", "||", "narrowpin")
        rp = c.ports["A"].get()
        self.assertEqual(int(rp.x2 - rp.x1), self.w // 2)

    def test_jog_on_the_pins_own_layer_has_no_cut(self):
        from cicpy.core.rect import Rect
        from cicpy.core.rules import Rules
        c = self._cell()
        w3 = int(Rules.getInstance().get("M3", "width"))
        pin = Rect("M3", 10 * w3, 30 * w3, 3 * w3, w3)
        before = len(c.children)
        x = int(pin.centerX()) + 5 * w3
        end = c._promoteJog("N", pin, "M3", x)
        added = c.children[before:]
        self.assertEqual(len(added), 1, "the bar and nothing else")
        bar = added[0]
        self.assertEqual(bar.layer, "M3")
        self.assertFalse(bar.isCut())
        #- from the pin's middle to x, at the pin's height
        self.assertLessEqual(int(bar.x1), int(pin.centerX()))
        self.assertGreaterEqual(int(bar.x2), x)
        self.assertEqual(int(bar.centerY()), int(pin.centerY()))
        self.assertEqual(end.layer, "M3")
        self.assertEqual(int(end.centerX()), x)

    def test_jog_to_another_layer_still_cuts(self):
        from cicpy.core.rect import Rect
        from cicpy.core.rules import Rules
        c = self._cell()
        w3 = int(Rules.getInstance().get("M3", "width"))
        pin = Rect("M3", 10 * w3, 30 * w3, 3 * w3, w3)
        before = len(c.children)
        end = c._promoteJog("N", pin, "M4",
                            int(pin.centerX()) + 5 * w3)
        added = c.children[before:]
        self.assertEqual(end.layer, "M4")
        self.assertTrue(any(a.isCut() or a.isInstance() for a in added))


if __name__ == "__main__":
    unittest.main()
