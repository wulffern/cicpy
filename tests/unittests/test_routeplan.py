"""The route plan: replayable only against the placement it saw.

The plan caches the maze router's conclusions; the one thing that
must never happen is a stale plan replaying against a moved
placement. These tests pin the contract: roundtrip, fingerprint
invalidation, the off switch, and that an `only` run keeps the other
stacks' entries.
"""
import os
import tempfile
import unittest


class FakeInstance:
    def __init__(self, name, cell, x, y):
        self.instanceName = name
        self.cell = cell
        self.x1 = x
        self.y1 = y


class FakeLayout:
    def __init__(self, dirname, name, instances):
        self.dirname = dirname
        self.name = name
        self._instances = [FakeInstance(*i) for i in instances]

    def iterInstances(self):
        return iter(self._instances)


ENTRY = {"stack": "p_in", "net": "VD1", "kind": "route",
         "layer": "M1", "rtype": "||", "opts": "trunkx=1000",
         "cuts": 1, "claims": [[1000, 0, 5000]]}


class RoutePlan(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dirname = self.tmp.name + os.path.sep
        os.environ.pop("CICPY_NO_ROUTEPLAN", None)

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("CICPY_NO_ROUTEPLAN", None)

    def _layout(self, instances=(("xa", "NCH", 0, 0),)):
        return FakeLayout(self.dirname, "TOP", list(instances))

    def test_roundtrip(self):
        from cicpy.core.routeplan import save_plan, load_plan
        lay = self._layout()
        save_plan(lay, [dict(ENTRY)], {"p_in"})
        plan = load_plan(lay)
        self.assertIsNotNone(plan)
        self.assertEqual(plan[("p_in", "VD1")]["opts"], "trunkx=1000")

    def test_moved_placement_invalidates(self):
        from cicpy.core.routeplan import save_plan, load_plan
        save_plan(self._layout(), [dict(ENTRY)], {"p_in"})
        moved = self._layout([("xa", "NCH", 400, 0)])
        self.assertIsNone(load_plan(moved))

    def test_new_instance_invalidates(self):
        from cicpy.core.routeplan import save_plan, load_plan
        save_plan(self._layout(), [dict(ENTRY)], {"p_in"})
        grown = self._layout([("xa", "NCH", 0, 0), ("xb", "NCH", 0, 800)])
        self.assertIsNone(load_plan(grown))

    def test_off_switch(self):
        from cicpy.core.routeplan import save_plan, load_plan
        lay = self._layout()
        save_plan(lay, [dict(ENTRY)], {"p_in"})
        os.environ["CICPY_NO_ROUTEPLAN"] = "1"
        self.assertIsNone(load_plan(lay))

    def test_only_run_keeps_other_stacks(self):
        from cicpy.core.routeplan import save_plan, load_plan
        lay = self._layout()
        other = dict(ENTRY, stack="p_sw", net="VCP")
        save_plan(lay, [dict(ENTRY), other], {"p_in", "p_sw"})
        plan = load_plan(lay)
        #- an `only` run over p_in alone rewrites p_in and must keep
        #- p_sw's stored entry
        save_plan(lay, [dict(ENTRY, opts="trunkx=2000")], {"p_in"},
                  previous=plan)
        plan2 = load_plan(lay)
        self.assertEqual(plan2[("p_in", "VD1")]["opts"], "trunkx=2000")
        self.assertIn(("p_sw", "VCP"), plan2)

    def test_no_file_no_plan(self):
        from cicpy.core.routeplan import load_plan
        self.assertIsNone(load_plan(self._layout()))


if __name__ == "__main__":
    unittest.main()
