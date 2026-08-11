"""The netlist split, against the plan's own example.

plans/subcells_plan.md states the transformation it wants, with a
worked TOP of eight pmos and ten caps. These are that example, so a
change that breaks the stated contract fails here rather than in a
layout three stages later.
"""
import re
import unittest

import cicspi as spi

from cicpy.core.hierarchy import plan_from_netlist, split_subckt


DEMO = """.subckt DEMO VBD1 LPI VDD_1V8
xca1<7> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<6> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<0> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xd1<9> LPI VDD_1V8 REYATR_CAPX1
xd1<1> LPI VDD_1V8 REYATR_CAPX1
xd1<0> LPI VDD_1V8 REYATR_CAPX1
.ends
"""

SPECS = [{"name": "pmos", "match": re.compile(r"^xca"), "type": "stack"},
         {"name": "caps", "match": re.compile(r"^xd"), "type": "stack"}]


def _parse(text=DEMO, name="DEMO"):
    #- NOT named TOP. SpiceParser.parseFile always appends a
    #- synthetic ".subckt TOP" wrapping whatever sat outside a subckt,
    #- and parses it LAST -- so a cell genuinely called TOP is silently
    #- overwritten by an empty one. Worth knowing before naming a cell.
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".spice")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    p = spi.SpiceParser()
    p.parseFile(path)
    os.unlink(path)
    return p, p[name]


class PlanFromNetlist(unittest.TestCase):

    def setUp(self):
        self.parser, self.ckt = _parse()

    def test_membership_is_the_designs_regex(self):
        plan = plan_from_netlist(self.ckt, SPECS)
        by = {e["stack"]: e for e in plan}
        self.assertEqual(len(by["pmos"]["instances"]), 3)
        self.assertEqual(len(by["caps"]["instances"]), 3)
        self.assertTrue(all(i.startswith("xca")
                            for i in by["pmos"]["instances"]))

    def test_first_spec_wins(self):
        """Declaration order is spec order, so a file reads specific to
        general and a broad regex later cannot steal an instance."""
        specs = [{"name": "first", "match": re.compile(r"^xca1<0>$")},
                 {"name": "rest", "match": re.compile(r"^xca")}]
        plan = plan_from_netlist(self.ckt, specs)
        by = {e["stack"]: e for e in plan}
        self.assertEqual(by["first"]["instances"], ["xca1<0>"])
        self.assertNotIn("xca1<0>", by["rest"]["instances"])

    def test_a_net_used_by_two_subcells_is_a_port(self):
        plan = plan_from_netlist(self.ckt, SPECS)
        by = {e["stack"]: e for e in plan}
        #- LPI and VDD_1V8 are on both; both are also parent ports
        self.assertIn("LPI", by["pmos"]["ports"])
        self.assertIn("LPI", by["caps"]["ports"])

    def test_a_parent_port_is_a_port_even_if_only_one_subcell_has_it(self):
        """The clause that matters: a differential input touches ONE
        column, and calling it internal buries the cell's own pin."""
        plan = plan_from_netlist(self.ckt, SPECS)
        by = {e["stack"]: e for e in plan}
        self.assertIn("VBD1", by["pmos"]["ports"])
        self.assertEqual(by["pmos"]["internal"], [])

    def test_a_net_shared_with_an_unclaimed_instance_is_a_port(self):
        """An instance no subcell claims stays in the parent, so a net
        it touches crosses a boundary."""
        specs = [{"name": "pmos", "match": re.compile(r"^xca")}]
        plan = plan_from_netlist(self.ckt, specs)
        self.assertIn("LPI", plan[0]["ports"])

    def test_names_are_parent_prefixed(self):
        plan = plan_from_netlist(self.ckt, SPECS)
        self.assertEqual({e["name"] for e in plan},
                         {"DEMO_PMOS", "DEMO_CAPS"})


class SplitSubckt(unittest.TestCase):

    def setUp(self):
        self.parser, self.ckt = _parse()
        self.plan = plan_from_netlist(self.ckt, SPECS)
        self.made = split_subckt(self.ckt, self.plan)

    def test_the_parent_becomes_its_subcells(self):
        """The transformation plans/subcells_plan.md asks for."""
        names = sorted(i.name for i in self.ckt.instances)
        self.assertEqual(names, ["xcaps", "xpmos"])
        self.assertEqual(sorted(i.subcktName for i in self.ckt.instances),
                         ["DEMO_CAPS", "DEMO_PMOS"])

    def test_the_devices_moved_and_did_not_copy(self):
        self.assertEqual(len(self.made["pmos"].instances), 3)
        self.assertEqual(len(self.made["caps"].instances), 3)

    def test_a_subckt_exports_its_boundary_not_every_node(self):
        caps = self.made["caps"]
        self.assertEqual(sorted(caps.nodes), ["LPI", "VDD_1V8"])

    def test_the_parents_index_is_rebuilt(self):
        """`instances` shrank; positional indices left behind return the
        wrong instance, or run off the end."""
        for inst in self.ckt.instances:
            self.assertIs(self.ckt.getInstance(inst.name), inst)

    def test_the_instance_line_does_not_alias_the_port_list(self):
        """Editing a child's ports must not silently edit the parent's
        connection order."""
        inst = self.ckt.getInstance("xcaps")
        self.assertIsNot(inst.nodes, self.made["caps"].nodes)

    def test_the_subckts_are_registered_for_lookup(self):
        self.assertIn("DEMO_PMOS", self.parser)
        self.assertIn("DEMO_CAPS", self.parser)

    def test_it_round_trips_to_spice(self):
        text = self.ckt.tospice()
        self.assertIn("xpmos", text)
        self.assertIn("DEMO_PMOS", text)
        self.assertNotIn("xca1<7>", text)


if __name__ == "__main__":
    unittest.main()
