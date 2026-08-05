#!/usr/bin/env python3
"""Fail if a transpiled mag file's FIXED_BBOX drifts from the cic cell box.

The cell box stored in the cic file is the abutment box the compiler placed
the cell on. Loading a design recomputes the live x1..y2 from the drawn
children, and for a while the magic printer wrote that content extent into
FIXED_BBOX instead of the stored box. Every consumer that placed cells by
FIXED_BBOX then lost the overlap tiling of stacked devices. This check
compares the FIXED_BBOX of every generated mag against the box stored in
the cic, so the two cannot drift apart again.

Usage: check_bbox.py <design.cic[.gz]> <magdir>
"""

import gzip
import json
import os
import re
import sys


def main():
    if len(sys.argv) != 3:
        print("usage: check_bbox.py <design.cic[.gz]> <magdir>")
        return 1

    cicfile, magdir = sys.argv[1], sys.argv[2]
    opener = gzip.open if cicfile.endswith(".gz") else open
    with opener(cicfile, "rt") as fi:
        design = json.load(fi)

    checked = 0
    bad = []
    for cell in design.get("cells", []):
        if not isinstance(cell, dict):
            continue
        name = cell.get("name")
        if not name or not all(k in cell for k in ("x1", "y1", "x2", "y2")):
            continue
        magfile = os.path.join(magdir, name + ".mag")
        if not os.path.isfile(magfile):
            continue
        m = re.search(r"FIXED_BBOX (-?\d+) (-?\d+) (-?\d+) (-?\d+)\s*$",
                      open(magfile).read(), re.M)
        checked += 1
        if m is None:
            bad.append(f"{name}: no parseable FIXED_BBOX in {magfile}")
            continue
        got = tuple(int(v) for v in m.groups())
        #- same scaling the printer uses, cic units to mag units
        want = tuple(int(round(cell[k] / 50)) for k in ("x1", "y1", "x2", "y2"))
        if got != want:
            bad.append(f"{name}: FIXED_BBOX {got} != cic box {want}")

    if checked == 0:
        print("check_bbox: no cells checked, that is a failure in itself")
        return 1

    if bad:
        print(f"check_bbox: {len(bad)} of {checked} cells drifted:")
        for b in bad[:20]:
            print(f"  {b}")
        return 1

    print(f"check_bbox: {checked} cells, FIXED_BBOX matches the cic box")
    return 0


if __name__ == "__main__":
    sys.exit(main())
