"""Wires in the sidecar: replayable only against the placement they saw.

The one thing that must never happen is a stale wires block replaying
its resolved coordinates against a moved stack. These tests pin the
contract: the fingerprint, the loud stale rejection, the off switch,
blocked entries, and the paste-ready formatting.
"""
import os
import unittest


class FakeInstance:
    def __init__(self, name, cell, x, y):
        self.instanceName = name
        self.cell = cell
        self.x1 = x
        self.y1 = y


STACK = [FakeInstance("xa", "NCH", 0, 0), FakeInstance("xb", "NCH", 0, 800)]

WIRES = [("VD1", "M1", "||", "trunkx=1000"),
         ("VSU", "blocked", "no column")]


class RoutePlan(unittest.TestCase):

    def setUp(self):
        os.environ.pop("CICPY_NO_ROUTEPLAN", None)

    def tearDown(self):
        os.environ.pop("CICPY_NO_ROUTEPLAN", None)

    def _entry(self, key):
        return {"name": "p_in", "wires": list(WIRES), "wires_key": key}

    def test_key_is_stable_and_position_sensitive(self):
        from cicpy.core.routeplan import stack_key
        k1 = stack_key(STACK)
        self.assertEqual(k1, stack_key(list(reversed(STACK))))
        moved = [FakeInstance("xa", "NCH", 400, 0), STACK[1]]
        self.assertNotEqual(k1, stack_key(moved))
        grown = STACK + [FakeInstance("xc", "NCH", 0, 1600)]
        self.assertNotEqual(k1, stack_key(grown))

    def test_matching_key_replays(self):
        from cicpy.core.routeplan import stack_key, wires_lookup
        key = stack_key(STACK)
        lut = wires_lookup(self._entry(key), key)
        self.assertIsNotNone(lut)
        self.assertEqual(lut["VD1"][3], "trunkx=1000")
        self.assertEqual(lut["VSU"][1], "blocked")

    def test_stale_key_is_rejected(self):
        from cicpy.core.routeplan import stack_key, wires_lookup
        key = stack_key(STACK)
        self.assertIsNone(wires_lookup(self._entry("deadbeef0000"), key))

    def test_off_switch(self):
        from cicpy.core.routeplan import stack_key, wires_lookup
        key = stack_key(STACK)
        os.environ["CICPY_NO_ROUTEPLAN"] = "1"
        self.assertIsNone(wires_lookup(self._entry(key), key))

    def test_no_declaration_no_replay(self):
        from cicpy.core.routeplan import wires_lookup
        self.assertIsNone(wires_lookup({"name": "p_in"}, "abc"))
        self.assertIsNone(wires_lookup(None, "abc"))

    def test_block_formats_as_pasteable_python(self):
        from cicpy.core.routeplan import format_wires_block
        block = format_wires_block("p_in", WIRES, "abc123")
        self.assertIn("wires = [", block)
        self.assertIn("('VD1', 'M1', '||', 'trunkx=1000'),", block)
        self.assertIn('wires_key = "abc123"', block)
        #- the body must be legal python when indented under a class
        src = "class p_in:\n" + "\n".join(
            l for l in block.splitlines() if not l.startswith("#"))
        ns = {}
        exec(src, ns)
        self.assertEqual(len(ns["p_in"].wires), 2)

    def test_replay_claims_from_trunkx_and_pins(self):
        from cicpy.core.routeplan import replay_claims

        class R:
            def __init__(s, x1, y1, x2, y2):
                s.x1, s.y1, s.x2, s.y2 = x1, y1, x2, y2

        pins = [R(900, 0, 1100, 400), R(900, 4000, 1100, 4400)]
        claims = replay_claims(pins, "M1", "M1", "trunkx=1000")
        self.assertEqual(claims, [(1000, 0, 4400)])
        #- a wire off the pin layer claims a landing per pin too
        claims = replay_claims(pins, "M2", "M1", "")
        self.assertEqual(len(claims), 2)


if __name__ == "__main__":
    unittest.main()
