"""A searched polyline, given back as a story.

The search emits paths (Path.fromNodes); their corners are coordinates,
and a coordinate may not enter a design file. path_suggestion resolves
each corner to a pin of the net or a track of a registered channel and
formats a paste-ready `paths` entry -- or marks the corner UNANCHORED,
loudly. These tests pin that contract.
"""
import unittest


class FakeRect:
    def __init__(self, layer, x1, y1, x2, y2):
        self.layer, self.x1, self.y1, self.x2, self.y2 = layer, x1, y1, x2, y2

    def centerX(self):
        return (self.x1 + self.x2) // 2

    def centerY(self):
        return (self.y1 + self.y2) // 2

    def get(self):
        return self


class FakePort:
    def __init__(self, name, rect):
        self.name, self._r = name, rect

    def isPort(self):
        return True

    def get(self):
        return self._r


class FakeInstance:
    def __init__(self, name, ports):
        self.instanceName = name
        self.children = ports


class FakeCell:
    """The three things the resolver reads: channels, pitch, pins."""

    def __init__(self):
        #- one vertical channel: tracks at 103000, 109000, 115000...
        self._routing_channels = {"dband": (100000, 160000, False)}
        self.pin_a = FakeRect("M2", 9000, 15000, 12200, 19000)
        self.pin_b = FakeRect("M5", 200000, 129300, 208800, 132700)
        self.instances = [
            FakeInstance("xa", [FakePort("N", self.pin_a)]),
            FakeInstance("xb", [FakePort("N", self.pin_b)]),
        ]

    def iterInstances(self):
        return iter(self.instances)

    def _lanePitch(self, layer=None):
        return 6000


def _entry(cell, nodes):
    from cicpy.core.routeplan import path_suggestion
    return path_suggestion(cell, "N",
                           [(cell.pin_a, cell.pin_b, nodes)])


class PathSuggest(unittest.TestCase):

    def test_corners_resolve_to_pins_and_tracks(self):
        cell = FakeCell()
        #- pin_a -> east to dband track 1 -> up -> north to pin_b's
        #- row -> east to pin_b. Node lists carry every grid step in
        #- the real thing; corners are what matters, so three nodes
        #- per leg stand in for it.
        nodes = [(10600, 17000, "M2"),
                 (109000, 17000, "M2"),
                 (109000, 17000, "M4"),
                 (109000, 131000, "M4"),
                 (204400, 131000, "M4")]
        text, unanchored = _entry(cell, nodes)
        self.assertEqual(unanchored, 0)
        self.assertIn('start=("xa", "N"), stop=("xb", "N")', text)
        self.assertIn('("movex", track("dband", 1)),', text)
        self.assertIn('("up", "M4"),', text)
        self.assertIn('("movey", pin("xb", "N", "y")),', text)
        self.assertIn('("movex", pin("xb", "N", "x")),', text)
        self.assertIn('("end",)]),', text)

    def test_pitch_offsets_from_a_pin_are_named(self):
        cell = FakeCell()
        #- the crossing row two lanes above pin_b: 131000 + 12000
        nodes = [(10600, 17000, "M2"),
                 (109000, 17000, "M2"),
                 (109000, 143000, "M2"),
                 (204400, 143000, "M2")]
        text, unanchored = _entry(cell, nodes)
        self.assertEqual(unanchored, 0)
        self.assertIn('pin("xb", "N", "y") + 2 * PITCH', text)

    def test_a_naked_coordinate_is_refused_loudly(self):
        cell = FakeCell()
        #- 77777 reproduces no pin and no track: it must come out
        #- UNANCHORED and the count must say so -- writing it as a
        #- number is the one thing this exists to prevent
        nodes = [(10600, 17000, "M2"),
                 (77777, 17000, "M2"),
                 (77777, 131000, "M2"),
                 (204400, 131000, "M2")]
        text, unanchored = _entry(cell, nodes)
        self.assertEqual(unanchored, 1)
        self.assertIn("UNANCHORED", text)
        self.assertIn('("movex", None),  #- x=77777', text)

    def test_down_is_emitted_when_the_stack_descends(self):
        cell = FakeCell()
        nodes = [(10600, 17000, "M4"),
                 (109000, 17000, "M4"),
                 (109000, 17000, "M2"),
                 (109000, 131000, "M2")]
        text, _ = _entry(cell, nodes)
        self.assertIn('("down", "M2"),', text)


if __name__ == "__main__":
    unittest.main()
