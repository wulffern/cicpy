#!/usr/bin/env python3
"""Tests for the cicpy-mcp server tools.

Skipped entirely when the optional `mcp` extra isn't installed, same
pattern as cicwave's MCP tests. The render tool needs a technology file
and a raster converter and is exercised by the design repositories, not
here; these tests cover the pure tools.
"""

import json
import os
import tempfile
import unittest

try:  # pragma: no cover - optional dependency
    import mcp as _mcp_pkg  # noqa: F401
    from cicpy.mcp_server import cell_info, layout_guide, netlist_info
    HAVE_MCP = True
except Exception:
    HAVE_MCP = False


@unittest.skipUnless(HAVE_MCP, "mcp package not installed (pip install cicpy[mcp])")
class McpToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, content):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as fo:
            fo.write(content)
        return path

    def test_layout_guide_returns_text(self):
        text = layout_guide()
        self.assertIn("layout", text.lower())

    def test_cell_info_lists_and_inspects(self):
        cic = self._write("t.cic", json.dumps({"cells": [
            {"name": "TOP", "x1": 0, "y1": 0, "x2": 800, "y2": 400,
             "children": [
                 {"class": "cIcCore::Instance", "instanceName": "xa1",
                  "cell": "DEV", "x1": 0, "y1": 0, "x2": 100, "y2": 100},
                 {"class": "cIcCore::Instance", "instanceName": "xa2",
                  "cell": "DEV", "x1": 0, "y1": 200, "x2": 100, "y2": 300},
                 {"class": "Port", "name": "A", "layer": "M1",
                  "x1": 0, "y1": 0, "x2": 10, "y2": 10},
                 {"class": "Port", "name": "B", "layer": "M1",
                  "x1": 5, "y1": 5, "x2": 5, "y2": 5},
             ]},
        ]}))
        listing = cell_info(cic)
        self.assertIn("TOP", listing)

        info = cell_info(cic, "TOP")
        self.assertIn("abutment box 0 0 800 400", info)
        self.assertIn("group xa", info)
        self.assertIn("pitches=[200]", info)
        #- the zero size port must be called out
        self.assertIn("NO GEOMETRY", info)
        self.assertNotIn("port A", [l for l in info.split("\n")
                                    if "NO GEOMETRY" in l][0])

    def test_netlist_info_reports_nets(self):
        spi = self._write("t.spi", "\n".join([
            ".subckt TOP A Y VSS",
            "xm1 Y A VSS VSS NCH",
            "+ extra=1",
            "xm2 Y A net1 VSS NCH",
            ".ends",
        ]))
        out = netlist_info(spi, "TOP")
        self.assertIn("ports: A Y VSS", out)
        self.assertIn("xm1 -> NCH", out)
        #- the continuation line must fold into xm2, not become a device
        self.assertNotIn("extra", out.split("nets:")[0].replace("extra=1", ""))
        self.assertIn("Y", out)
        self.assertRegex(out, r"Y\s+xm1\.0 xm2\.0")

    def test_netlist_info_missing_subckt(self):
        spi = self._write("t.spi", ".subckt OTHER A\n.ends\n")
        self.assertIn("no subckt", netlist_info(spi, "TOP"))


if __name__ == "__main__":
    unittest.main()
