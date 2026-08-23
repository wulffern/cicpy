#!/usr/bin/env python3
"""Structurally compare two .cic files.

Parity with ciccreator is a question about GEOMETRY, not about bytes.
The two writers disagree on bookkeeping keys -- cicpy emits "ckt",
ciccreator emits "libcell"/"meta"/"physicalOnly" -- and neither
difference moves a single rectangle. So compare what the layout
actually is: per cell, the multiset of shapes its children describe.

Exit 0 when the designs match, 1 when they do not, and print the
first differences in a form that says which cell to go look at.
"""
import gzip
import json
import sys
from collections import Counter

#- Keys that describe a shape. Anything else in a child object is
#- bookkeeping that the two writers are entitled to disagree on.
#- `net` is NOT here: ciccreator writes "" for nearly every shape,
#- while cicpy attributes wires and cuts to their net on purpose --
#- the same geometry, one writer keeping more of what it knew. Net
#- ATTRIBUTION is checked by cicpy's own connectivity tools, not by
#- this comparator.
SHAPE = ("class", "layer", "x1", "y1", "x2", "y2")


def load(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fi:
        return json.load(fi)


def shapes(node, out, depth=0):
    """Flatten a cell's children into hashable shape tuples."""
    for child in node.get("children", []) or []:
        cls = child.get("class", "")
        key = [cls]
        for k in SHAPE[1:]:
            v = child.get(k, "")
            key.append(v)
        #- an Instance names the cell it places; that is geometry too
        if "cell" in child:
            key.append(child["cell"])
        if "name" in child and cls != "Rect":
            key.append(child["name"])
        out[tuple(key)] += 1
        shapes(child, out, depth + 1)


def index(design):
    cells = {}
    for c in design.get("cells", []):
        counter = Counter()
        shapes(c, counter)
        cells[c.get("name", "?")] = counter
    return cells


def main(argv):
    if len(argv) < 3:
        print("usage: compare_cic.py <reference.cic> <candidate.cic> [--max N]")
        return 2
    ref, cand = index(load(argv[1])), index(load(argv[2]))
    limit = 12
    if "--max" in argv:
        limit = int(argv[argv.index("--max") + 1])

    only_ref = sorted(set(ref) - set(cand))
    only_cand = sorted(set(cand) - set(ref))
    shared = sorted(set(ref) & set(cand))

    differing = [n for n in shared if ref[n] != cand[n]]

    total_ref = sum(sum(c.values()) for c in ref.values())
    total_cand = sum(sum(c.values()) for c in cand.values())

    print("reference : %-28s %4d cells, %6d shapes" % (argv[1].split("/")[-1], len(ref), total_ref))
    print("candidate : %-28s %4d cells, %6d shapes" % (argv[2].split("/")[-1], len(cand), total_cand))
    print()

    ok = True
    if only_ref:
        ok = False
        print("MISSING from candidate (%d cells):" % len(only_ref))
        for n in only_ref[:limit]:
            print("    %s  (%d shapes)" % (n, sum(ref[n].values())))
        if len(only_ref) > limit:
            print("    ... and %d more" % (len(only_ref) - limit))
        print()
    if only_cand:
        ok = False
        print("EXTRA in candidate (%d cells):" % len(only_cand))
        for n in only_cand[:limit]:
            print("    %s" % n)
        if len(only_cand) > limit:
            print("    ... and %d more" % (len(only_cand) - limit))
        print()
    if differing:
        ok = False
        print("GEOMETRY DIFFERS in %d of %d shared cells:" % (len(differing), len(shared)))
        for n in differing[:limit]:
            missing = ref[n] - cand[n]
            extra = cand[n] - ref[n]
            print("    %-28s -%-4d +%-4d shapes" % (n, sum(missing.values()), sum(extra.values())))
            for shape, cnt in list(missing.items())[:2]:
                print("         want %dx %s" % (cnt, shape))
            for shape, cnt in list(extra.items())[:2]:
                print("         got  %dx %s" % (cnt, shape))
        if len(differing) > limit:
            print("    ... and %d more" % (len(differing) - limit))
        print()

    matched = len(shared) - len(differing)
    print("PARITY: %d/%d cells match exactly (%.1f%%)" % (
        matched, len(ref), 100.0 * matched / len(ref) if ref else 0.0))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
