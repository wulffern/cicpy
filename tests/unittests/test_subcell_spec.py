"""The subcell declarations in the cell sidecar: <CELL>.py.

A subcell is a statement about the design -- which devices form a unit,
and what kind -- and the sidecar is where that statement lives: a
SidecarCell subclass with nested Subcell classes. These tests pin the
contract: what parses, what is rejected, that declaration order decides
membership, and that an undeclared type is "stack".

WHERE THAT CONTRACT LIVES MOVED, and these tests moved with it. A
cell is assembled from `subcells` -- other cells -- and places devices
into `stacks`; the two are mutually exclusive and a child has stacks
and no subcells (see "a declared piece is a cell"). So a SIDECAR's
nested classes compile to `subcells`, and `subcell_spec`, which reads
`stacks`, is about a built child rather than about the file. These
read the file through `load_sidecar_spec` and the membership rule
through `plan_from_netlist`, which is what consumes it.

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


class FakeSpiceInstance:
    def __init__(self, name):
        self.name = name
        self.nodes = []


class FakeCkt:
    """Just enough of a Subckt for plan_from_netlist."""

    def __init__(self, names, nodes=()):
        self.name = "FAKE"
        self.instances = [FakeSpiceInstance(n) for n in names]
        self.nodes = list(nodes)


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
        from cicpy.sidecar import load_sidecar_spec
        self._write("PARSES", """
class PARSES(SidecarCell):
    class p_in(DiffPair):
        match = "^xbl"
    class ladder(Stack):
        match = "^xbs"
""")
        spec = load_sidecar_spec(self.dirname, "PARSES")["subcells"]
        self.assertEqual([e["name"] for e in spec], ["p_in", "ladder"])
        self.assertEqual(spec[0]["type"], "diffpair")
        #- undeclared type is a stack: that is what an undeclared
        #- subcell IS
        self.assertEqual(spec[1]["type"], "stack")

    def test_an_entry_without_match_is_dropped(self):
        from cicpy.sidecar import load_sidecar_spec
        self._write("NOMATCH", """
class NOMATCH(SidecarCell):
    class nameless(Stack):
        pass
    class ok(Stack):
        match = "^xok"
""")
        spec = load_sidecar_spec(self.dirname, "NOMATCH")["subcells"]
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_a_bad_regex_is_dropped_not_fatal(self):
        from cicpy.sidecar import load_sidecar_spec
        self._write("BADRX", """
class BADRX(SidecarCell):
    class broken(Stack):
        match = "["
    class ok(Stack):
        match = "^xok"
""")
        spec = load_sidecar_spec(self.dirname, "BADRX")["subcells"]
        self.assertEqual([e["name"] for e in spec], ["ok"])

    def test_membership_first_entry_wins(self):
        """Declaration order decides; read specific to general."""
        from cicpy.sidecar import load_sidecar_spec
        from cicpy.core.hierarchy import plan_from_netlist
        self._write("FIRSTWINS", """
class FIRSTWINS(SidecarCell):
    class special(Stack):
        match = "^xbl4$"
    class p_in(Stack):
        match = "^xbl"
""")
        spec = load_sidecar_spec(self.dirname, "FIRSTWINS")["subcells"]
        plan = plan_from_netlist(
            FakeCkt(["xbl4", "xbl5", "xother"]), spec, "FIRSTWINS")
        owned = {e["stack"]: e["instances"] for e in plan}
        self.assertEqual(owned.get("special"), ["xbl4"])
        self.assertEqual(owned.get("p_in"), ["xbl5"])
        #- an instance no entry claims stays with the parent
        self.assertNotIn("xother",
                         [i for v in owned.values() for i in v])

    def test_plan_carries_the_type(self):
        """plan_from_netlist rides the declared type on each entry."""
        from cicpy.sidecar import load_sidecar_spec
        from cicpy.core.hierarchy import plan_from_netlist
        self._write("TYPED", """
class TYPED(SidecarCell):
    class p_in(DiffPair):
        match = "^xbl"
    class ladder(Stack):
        match = "^xbs"
""")
        spec = load_sidecar_spec(self.dirname, "TYPED")["subcells"]
        plan = plan_from_netlist(FakeCkt(["xbl1", "xbs1"]), spec, "TYPED")
        types = {e["stack"]: e["type"] for e in plan}
        self.assertEqual(types.get("p_in"), "diffpair")
        self.assertEqual(types.get("ladder"), "stack")
