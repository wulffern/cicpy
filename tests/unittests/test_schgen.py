"""cicpy.eda.schgen: pins read from the symbol, labels on the pins,
box symbols."""
import os
import tempfile
import unittest

from cicpy.eda.schgen import (Sheet, Symbol, bus, nets, box_symbol,
                              LEFT, RIGHT, UP, DOWN)

#- a MOS-like symbol: gate left, source top, drain bottom, bulk right
PCH = """v {xschem version=3.4.7 file_version=1.2}
K {type=subcircuit}
L 4 20 -30 40 -30 {}
L 4 20 30 40 30 {}
L 4 0 0 20 0 {}
B 5 36 34 44 26 {name=D dir=inout}
B 5 -4 4 4 -4 {name=G dir=inout}
B 5 36 -26 44 -34 {name=S dir=inout}
B 5 36 4 44 -4 {name=B dir=inout}
"""


class TestSchgen(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "LIB"))
        with open(os.path.join(self.tmp.name, "LIB", "PCH.sym"), "w") as f:
            f.write(PCH)

    def tearDown(self):
        self.tmp.cleanup()

    def test_symbol_sides(self):
        s = Symbol(os.path.join(self.tmp.name, "LIB", "PCH.sym"))
        self.assertEqual(s.pins["G"], (0, 0, LEFT))
        self.assertEqual(s.pins["S"], (40, -30, UP))
        self.assertEqual(s.pins["D"], (40, 30, DOWN))
        self.assertEqual(s.pins["B"], (40, 0, RIGHT))

    def test_inst_labels_and_pin(self):
        sh = Sheet("C", [("A", "in"), ("Y", "out")], search=[self.tmp.name])
        sh.inst("LIB/PCH.sym", bus("xp", 4), 100, 200, G="A", D="Y")
        self.assertEqual(sh.pin("xp[3:0]", "S"), (140, 170))
        sch = "\n".join(sh.L)
        self.assertIn("C {LIB/PCH.sym} 100 200 0 0 {name=xp[3:0]}", sch)
        self.assertIn("C {devices/lab_pin.sym} 100 200 0 0", sch)
        self.assertIn("C {devices/lab_pin.sym} 140 230 1 0", sch)
        with self.assertRaises(KeyError):
            sh.inst("LIB/PCH.sym", "xq", 0, 0, X="A")

    def test_write_and_box(self):
        pins = [("VDD", "in"), ("A", "in"), ("Y", "out")]
        sh = Sheet("C", pins, search=[self.tmp.name], title="t")
        sh.wlab(0, 0, 100, 0, UP, "N")
        sh.write(self.tmp.name)
        s = Symbol(os.path.join(self.tmp.name, "C.sym"))
        b = box_symbol(pins)
        for p in ("VDD", "A", "Y"):
            self.assertEqual(s.pins[p][:2], b.pins[p][:2])
        self.assertEqual(s.pins["A"][2], LEFT)
        self.assertEqual(s.pins["Y"][2], RIGHT)
        with open(os.path.join(self.tmp.name, "C.sch")) as f:
            txt = f.read()
        self.assertIn("N 0 0 50 0 {}", txt)
        self.assertIn("N 50 0 100 0 {}", txt)

    def test_nets(self):
        self.assertEqual(nets("N", range(2, -1, -1)), "N2,N1,N0")
        self.assertEqual(bus("x", 1), "x")


if __name__ == "__main__":
    unittest.main()
