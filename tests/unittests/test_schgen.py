"""cicpy.eda.schgen: pins read from the symbol, labels on the pins,
box symbols."""
import os
import tempfile
import unittest

from cicpy.eda.schgen import (Sheet, Symbol, bus, nets, box_symbol,
                              frame, port_row, LEFT, RIGHT, UP, DOWN)

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
        #- the drain is under the body: its label hangs below, rot 3
        self.assertIn("C {devices/lab_pin.sym} 140 230 3 0", sch)
        self.assertEqual((LEFT, UP, RIGHT, DOWN), (0, 1, 2, 3))
        with self.assertRaises(KeyError):
            sh.inst("LIB/PCH.sym", "xq", 0, 0, X="A")

    def test_inst_sides(self):
        """sides turns one pin's label; the others keep their own."""
        sh = Sheet("C", [("A", "in")], search=[self.tmp.name])
        sh.inst("LIB/PCH.sym", "xp", 0, 0, sides={"S": RIGHT},
                S="VDD", D="Y")
        sch = "\n".join(sh.L)
        self.assertIn(f"C {{devices/lab_pin.sym}} 40 -30 {RIGHT} 0", sch)
        self.assertIn(f"C {{devices/lab_pin.sym}} 40 30 {DOWN} 0", sch)

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

    def test_frame_holds_the_text(self):
        #- xschem plots without the text in its fit: the frame is what
        #- keeps a title and a long note on the page
        L = ["T {a title of thirty characters..} -100 -200 0 0 0.5 0.5 {}",
             "N 0 0 300 0 {}",
             "C {devices/lab_pin.sym} 300 0 2 0 {name=l1 lab=LONGNAME}",
             "C {devices/lab_pin.sym} 0 0 3 0 {name=l2 lab=VSS}"]
        out = frame(L)
        self.assertEqual(out[:-1], L)
        v = list(map(float, out[-1].split("{")[0].split()[3:]))
        xs, ys = v[0::2], v[1::2]
        self.assertLessEqual(min(xs), -100 - 40)
        self.assertLessEqual(min(ys), -200 - 40)
        #- the title is 30 characters of size 0.5, about 375 wide
        self.assertGreaterEqual(max(xs), -100 + 375 + 40)
        #- VSS hangs below the wire
        self.assertGreater(max(ys), 40 + 40)
        self.assertTrue(out[-1].startswith("P 4 5 "))

    def test_frame_uses_the_boxes(self):
        L = ["C {LIB/BIG.sym} 0 0 0 0 {name=x1}"]
        v = frame(L, boxes=[(-150, -300, 150, 300)])[-1].split()
        self.assertEqual(v[3:5], ["-190", "-340"])
        v = frame(L)[-1].split()
        self.assertEqual(v[3:5], ["-190", "-190"])

    def test_port_row_makes_room(self):
        #- short names keep the pitch; a long output before an input
        #- pushes the input along
        x = [int(l.split()[2]) for l in port_row(
            [("A", "in"), ("B", "in"), ("uio_oe[7:0]", "out"),
             ("VDPWR", "in")])]
        self.assertEqual(x[:3], [-1400, -1240, -1080])
        self.assertGreater(x[3] - x[2], 160)

    def test_written_sheet_has_a_frame(self):
        sh = Sheet("CELL", [("A", "in")], search=[self.tmp.name],
                   title="CELL: a title")
        sh.inst("LIB/PCH.sym", "xp", 0, 0, G="A")
        sh.write(self.tmp.name, symbol=False)
        with open(os.path.join(self.tmp.name, "CELL.sch")) as f:
            self.assertTrue(f.read().rstrip().endswith("{dash=4}"))

    def test_nets(self):
        self.assertEqual(nets("N", range(2, -1, -1)), "N2,N1,N0")
        self.assertEqual(bus("x", 1), "x")


if __name__ == "__main__":
    unittest.main()
