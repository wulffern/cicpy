"""TrackMap's pin model, against a layout whose failure is known.

These are regression tests for a bug that was invisible for a long time
because nothing looked for it: `_collectPhysicalRects` skips ports, so
no pin ever reached the track map, and every router question was
answered as if pins did not exist. Four separate routing failures in
LELOTEMP_OTAR were the same thing -- a route laid through another net's
pin.

The fixture is that layout, so a regression here is a regression against
a measured short rather than against a made-up one.
"""
import os
import unittest

IP = os.path.join(os.path.dirname(__file__), "..", "..", "..")
CIC = os.path.join(IP, "lelo_temp_sky130a", "design",
                   "LELO_TEMP_SKY130A", "LELOTEMP_OTAR.cic")
LIB = os.path.join(IP, "rey_atr_sky130a", "design", "REY_ATR_SKY130A.cic")
TECH = os.path.join(IP, "tech_sky130A", "cic", "sky130.tech")

#- the measured collision: VS drops a via column into the resistor to
#- reach its pin, and passes VDS's pin at y 104000 on the way
RES_COLUMN = (265200, 274200)
VS_SPAN = (57300, 290700)


def _have_fixture():
    return all(os.path.exists(p) for p in (CIC, LIB, TECH))


@unittest.skipUnless(_have_fixture(), "LELOTEMP_OTAR fixture not present")
class TrackMapPins(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from cicpy.cic import load_design
        from cicpy.core.rules import Rules
        from cicpy.core.trackmap import TrackMap
        Rules(TECH)
        design = load_design(CIC, [LIB])
        cls.cell = design.cells["LELOTEMP_OTAR"]
        cls.plain = TrackMap(cls.cell).build()
        cls.pins = TrackMap(cls.cell, block_pins=True).build()

    def test_pins_off_by_default(self):
        """The default must not change: block_pins is opt-in."""
        n = sum(len(t.pins) for l in self.plain.tracks
                for t in self.plain.tracks[l])
        self.assertEqual(n, 0)

    def test_pins_are_found(self):
        n = sum(len(t.pins) for l in self.pins.tracks
                for t in self.pins.tracks[l])
        self.assertGreater(n, 0, "no pins reached the track map")

    def test_pin_nets_are_real_nets(self):
        """Not cell-local port names.

        Attributing a pin from its own port name gives B, S, P, N -- the
        subcell's names for its terminals, which say nothing about which
        net the instance is wired to. The node graph is the only source
        that knows.
        """
        nets = {n for l in self.pins.tracks for t in self.pins.tracks[l]
                for n in t.pins}
        self.assertIn("VDS", nets)
        self.assertIn("VS", nets)
        self.assertNotIn("B", nets)
        self.assertNotIn("S", nets)

    def test_column_blockers_finds_the_known_collision(self):
        """The one the short report blamed."""
        hits = self.pins.column_blockers("VS", *RES_COLUMN, *VS_SPAN)
        nets = {h[0] for h in hits}
        self.assertIn("VDS", nets)

    def test_column_blockers_is_clean_where_nothing_is(self):
        """A control, so the test above is not just 'returns something'."""
        hits = self.pins.column_blockers("VS", *RES_COLUMN, 240000, 250000)
        self.assertEqual(hits, [])

    def test_a_net_does_not_block_itself(self):
        hits = self.pins.column_blockers("VDS", *RES_COLUMN, *VS_SPAN)
        self.assertNotIn("VDS", {h[0] for h in hits})

    def test_same_layer_test_does_not_catch_it(self):
        """Why column_blockers exists at all.

        VS's trunk is on M4 and VDS's pin is on M1, so they never share a
        track and a same-layer test reports nothing. This asserts the
        limitation, so that if someone 'simplifies' column_blockers back
        to a per-layer check the reason is right here.
        """
        free = self.pins.free_between("M4", *VS_SPAN, *RES_COLUMN)
        aware = self.pins.free_for("VS", "M4", *VS_SPAN, *RES_COLUMN)
        self.assertEqual(sorted(free), sorted(aware))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(_have_fixture(), "LELOTEMP_OTAR fixture not present")
class TechDriven(unittest.TestCase):
    """The router must be a router, not a sky130 router.

    Everything about the stack comes from the technology file. These
    tests exist because the first version hard coded all of it: M1 was
    the pin layer, M2/M4 were vertical, the layer order was
    `sorted(names)`, and a via pad was 8800 because a note said so.
    """

    @classmethod
    def setUpClass(cls):
        from cicpy.cic import load_design
        from cicpy.core.rules import Rules
        Rules(TECH)
        cls.cell = load_design(CIC, [LIB]).cells["LELOTEMP_OTAR"]

    def _map(self, **kw):
        from cicpy.core.trackmap import TrackMap
        return TrackMap(self.cell, **kw)

    def test_pin_layer_comes_from_the_tech(self):
        self.assertEqual(self._map().pin_layer, "M1")

    def test_directions_come_from_the_tech(self):
        self.assertEqual(self._map().directions,
                         {"M2": "v", "M3": "h", "M4": "v", "M5": "h"})

    def test_stack_order_follows_the_layer_chain_not_the_names(self):
        """sorted() happens to work for M1..M5 and puts M10 between M1
        and M2 the moment a technology has one."""
        self.assertEqual(self._map().metal_stack(),
                         ["M1", "M2", "M3", "M4", "M5"])

    def test_no_layer_names_are_hard_coded_in_the_modules(self):
        import re, os
        import cicpy.core.trackmap as tmmod
        import cicpy.core.mazerouter as mrmod
        for mod in (tmmod, mrmod):
            with open(mod.__file__) as fi:
                src = fi.read()
            #- strip comments: the reasoning may name layers, the code
            #- may not
            code = "\n".join(l for l in src.splitlines()
                             if not l.strip().startswith("#"))
            hits = re.findall(r'"(M\d+|VIA\d+)"', code)
            self.assertEqual(hits, [],
                             f"{os.path.basename(mod.__file__)} hard codes {hits}")

    def test_via_size_is_asked_for_not_assumed(self):
        from cicpy.core.mazerouter import MazeRouter
        r = MazeRouter(self._map(block_pins=True).build(), "VS")
        stack = r._layers
        self.assertGreater(len(stack), 1)
        w, h = r.via_extent(stack[0], stack[1])
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)


@unittest.skipUnless(_have_fixture(), "LELOTEMP_OTAR fixture not present")
class StackSubckt(unittest.TestCase):
    """The generated schematic side of a stack subcell.

    Generated, never edited -- which is the answer to a hand-maintained
    substack schematic drifting from its layout: there is nothing to
    drift, because both sides come from the same netlist and are rebuilt
    together every run. The fingerprint guards what regeneration cannot,
    which is the GROUPING changing silently: instance names decide
    placement groups, so a rename moves a device to another stack and
    both sides then agree, wrongly and consistently.
    """

    @classmethod
    def setUpClass(cls):
        from cicpy.cic import load_design
        from cicpy.core.rules import Rules
        from cicpy.core.mazerouter import plan_stack_cells
        Rules(TECH)
        cls.cell = load_design(CIC, [LIB]).cells["LELOTEMP_OTAR"]
        cls.plan = plan_stack_cells(cls.cell)
        cls.big = max(cls.plan, key=lambda p: len(p["instances"]))

    def _subckt(self, entry):
        from cicpy.core.mazerouter import stack_subckt
        return stack_subckt(self.cell, entry)

    def test_header_declares_exactly_the_boundary_nets(self):
        lines, _fp = self._subckt(self.big)
        header = lines[0].split()
        self.assertEqual(header[0], ".subckt")
        self.assertEqual(header[1], self.big["name"])
        self.assertEqual(sorted(header[2:]), sorted(self.big["ports"]))

    def test_internal_nets_are_not_ports(self):
        """The whole point: what is internal stops existing above."""
        lines, _fp = self._subckt(self.big)
        ports = set(lines[0].split()[2:])
        for net in self.big["internal"]:
            self.assertNotIn(net, ports)

    def test_every_connected_instance_appears_once(self):
        """Instances with NODES, which is not all of them.

        Taps and fillers have none -- they are layout, not circuit --
        and are deliberately left out. And a design loaded from a .cic
        has no node information at all, so on this fixture the body is
        empty; the assertion is then that it is empty rather than wrong,
        and the real check runs in the flow.
        """
        lines, _fp = self._subckt(self.big)
        names = [l.split()[0] for l in lines[1:-1]]
        self.assertEqual(len(names), len(set(names)), "an instance twice")
        self.assertTrue(set(names) <= set(self.big["instances"]),
                        "emitted an instance that is not in this stack")
        connected = [i for i in self.big["instances"]
                     if getattr(self._inst(i), "instancePortsList", None)]
        self.assertEqual(sorted(names), sorted(connected))

    def _inst(self, name):
        for inst in self.cell.iterInstances():
            if (getattr(inst, "instanceName", "") or "") == name:
                return inst
        return None

    def test_it_is_terminated(self):
        lines, _fp = self._subckt(self.big)
        self.assertEqual(lines[-1], ".ends")

    def test_fingerprint_is_stable_and_sensitive(self):
        _l, a = self._subckt(self.big)
        _l, b = self._subckt(self.big)
        self.assertEqual(a, b, "same stack must fingerprint the same")
        moved = dict(self.big)
        moved["ports"] = sorted(set(self.big["ports"]) | {"__EXTRA__"})
        _l, c = self._subckt(moved)
        self.assertNotEqual(a, c, "a changed boundary must change the print")
