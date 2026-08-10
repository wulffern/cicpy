"""The subcell declarations in the cell sidecar: <CELL>.py.

A subcell is a statement about the design -- which devices form a unit,
and what kind -- and the sidecar is where that statement lives: a
SidecarCell subclass with nested Subcell classes. These tests pin the
contract: what parses, what is rejected, that declaration order decides
membership, and that an undeclared type is "stack".

Each test uses a UNIQUE cell name: the sidecar import goes through
sys.modules, so a second module of the same name would silently reuse
the first.
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


HEADER = "from cicpy.sidecar import SidecarCell, Stack, DiffPair\n"


class SubcellSpec(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dirname = self.tmp.name + os.path.sep

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, cellname, text):
        with open(os.path.join(self.dirname, cellname + ".py"), "w") as f:
            f.write(HEADER + text)

    def _layout(self, cellname, instances=()):
        return FakeLayout(self.dirname, cellname, instances)

    def test_no_file_is_no_spec(self):
        from cicpy.core.mazerouter import subcell_spec
        self.assertEqual(subcell_spec(self._layout("NOFILE")), [])

    def test_name_match_and_type_parse(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("PARSES", """
class PARSES(SidecarCell):
    class p_in(DiffPair):
        match = "^xbl"
    class ladder(Stack):
        match = "^xbs"
""")
        spec = subcell_spec(self._layout("PARSES"))
        self.assertEqual([e["name"] for e in spec], ["p_in", "ladder"])
        self.assertEqual(spec[0]["type"], "diffpair")
        #- undeclared type is a stack: that is what an undeclared
        #- subcell IS
        self.assertEqual(spec[1]["type"], "stack")

    def test_an_entry_without_match_is_dropped(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("NOMATCH", """
class NOMATCH(SidecarCell):
    class nameless(Stack):
        pass
    class ok(Stack):
        match = "^xok"
""")
        spec = subcell_spec(self._layout("NOMATCH"))
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_a_bad_regex_is_dropped_not_fatal(self):
        from cicpy.core.mazerouter import subcell_spec
        self._write("BADRX", """
class BADRX(SidecarCell):
    class broken(Stack):
        match = "["
    class ok(Stack):
        match = "^xok"
""")
        spec = subcell_spec(self._layout("BADRX"))
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_membership_first_entry_wins(self):
        from cicpy.core.mazerouter import subcell_membership
        self._write("FIRSTWINS", """
class FIRSTWINS(SidecarCell):
    class special(Stack):
        match = "^xbl4$"
    class p_in(Stack):
        match = "^xbl"
""")
        member = subcell_membership(
            self._layout("FIRSTWINS", ["xbl4", "xbl5", "xother"]))
        self.assertEqual(member.get("xbl4"), "special")
        self.assertEqual(member.get("xbl5"), "p_in")
        self.assertNotIn("xother", member)

    def test_plan_carries_the_type(self):
        """plan_subcells rides the declared type on each entry."""
        from cicpy.core.mazerouter import subcell_spec
        self._write("TYPED", """
class TYPED(SidecarCell):
    class p_in(DiffPair):
        match = "^xbl"
""")
        types = {e["name"]: e["type"]
                 for e in subcell_spec(self._layout("TYPED"))}
        self.assertEqual(types.get("p_in", "stack"), "diffpair")
        self.assertEqual(types.get("undeclared", "stack"), "stack")


if __name__ == "__main__":
    unittest.main()
