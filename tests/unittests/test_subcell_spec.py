"""The subcell sidecar: <CELL>.subcells.yaml.

A subcell is a statement about the design -- which devices form a unit,
and what kind -- and the sidecar is where that statement lives. These
tests pin the contract: what parses, what is rejected, that the sidecar
takes precedence over the group walk, and that an undeclared subcell is
of type "stack".
"""
import os
import tempfile
import unittest


class FakeInstance:
    def __init__(self, name):
        self.instanceName = name


class FakeLayout:
    """Just enough of a LayoutCell for the membership walk."""

    def __init__(self, dirname, name, instances):
        self.dirname = dirname
        self.name = name
        self._instances = [FakeInstance(n) for n in instances]
        self.cellgroups = []

    def iterInstances(self):
        return iter(self._instances)


class SubcellSpec(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dirname = self.tmp.name + os.path.sep

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        with open(os.path.join(self.dirname, "TOP.subcells.yaml"), "w") as f:
            f.write(text)

    def _layout(self, instances=()):
        return FakeLayout(self.dirname, "TOP", instances)

    def test_no_file_is_no_spec(self):
        from cicpy.core.mazerouter import subcell_spec
        self.assertEqual(subcell_spec(self._layout()), [])

    def test_name_match_and_type_parse(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("""
subcells:
  - name: p_in
    match: "^xbl"
    type: diffpair
  - name: ladder
    match: "^xbs"
""")
        spec = subcell_spec(self._layout())
        self.assertEqual([e["name"] for e in spec], ["p_in", "ladder"])
        self.assertEqual(spec[0]["type"], "diffpair")
        #- undeclared type is a stack: that is what an undeclared
        #- subcell IS
        self.assertEqual(spec[1]["type"], "stack")

    def test_an_entry_without_name_or_match_is_dropped(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("""
subcells:
  - name: nameless
  - match: "^x"
  - name: ok
    match: "^xok"
""")
        spec = subcell_spec(self._layout())
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_a_bad_regex_is_dropped_not_fatal(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("""
subcells:
  - name: broken
    match: "["
  - name: ok
    match: "^xok"
""")
        spec = subcell_spec(self._layout())
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_membership_first_entry_wins(self):
        from cicpy.core.mazerouter import subcell_membership
        self._write("""
subcells:
  - name: special
    match: "^xbl4$"
  - name: p_in
    match: "^xbl"
""")
        member = subcell_membership(
            self._layout(["xbl4", "xbl5", "xother"]))
        self.assertEqual(member.get("xbl4"), "special")
        self.assertEqual(member.get("xbl5"), "p_in")
        self.assertNotIn("xother", member)

    def test_plan_carries_the_type(self):
        """plan_subcells rides the declared type on each entry."""
        from cicpy.core.mazerouter import subcell_spec
        self._write("""
subcells:
  - name: p_in
    match: "^xbl"
    type: diffpair
""")
        types = {e["name"]: e["type"] for e in subcell_spec(self._layout())}
        self.assertEqual(types.get("p_in", "stack"), "diffpair")
        self.assertEqual(types.get("undeclared", "stack"), "stack")


if __name__ == "__main__":
    unittest.main()
