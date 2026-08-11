"""What a cell's routing COST, in the terms a reviewer argues in.

A route can be correct and still be bad: DRC and LVS both pass on a
net that reached its pins by climbing two layers, crossing, and coming
back down at every device. Nothing in the flow said so -- the only
numbers were 0 and "match uniquely", and by those the weaving version
and the two clean rails were the same answer.

So: length, vias, and pieces.

  length   the wire, in um. The wire is the resistance and most of the
           capacitance, and on an analog net it is the spec.
  vias     each one is a resistance, a reliability risk and a hole in
           the layer above. A route that needs none is worth a lot.
  pieces   how many rectangles it took. Not a cost in silicon, but a
           very good smell: a net drawn in forty pieces was drawn by
           something that did not know what it was drawing.

Reported per net so a regression names itself, and totalled so two
builds can be compared in one line.
"""
import gzip
import json
import logging

log = logging.getLogger("WireCost")


def _iter_rects(obj, out):
    """Every rect in a cell's tree, routed or not."""
    if isinstance(obj, dict):
        if obj.get("class") == "Rect":
            out.append(obj)
        for v in obj.values():
            _iter_rects(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _iter_rects(v, out)
    return out


def _iter_cuts(obj, out):
    if isinstance(obj, dict):
        cls = obj.get("class", "")
        if cls in ("Cut", "InstanceCut"):
            out.append(obj)
        else:
            for v in obj.values():
                _iter_cuts(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _iter_cuts(v, out)
    return out


def cell_cost(cell, um=10000):
    """{net: {length, vias, pieces}} plus a "" total, for one cell dict.

    Length is the LONG side of each rect: a wire's cost is how far it
    goes, not how much metal it is. A via's enclosure is not wire and
    is not counted as any.
    """
    per = {}

    def bucket(net):
        return per.setdefault(net or "?", {"length": 0.0, "vias": 0,
                                           "pieces": 0})

    for r in _iter_rects(cell, []):
        net = r.get("net", "")
        if not net:
            continue
        w = abs(float(r.get("x2", 0)) - float(r.get("x1", 0)))
        h = abs(float(r.get("y2", 0)) - float(r.get("y1", 0)))
        b = bucket(net)
        b["length"] += max(w, h) / float(um)
        b["pieces"] += 1

    for c in _iter_cuts(cell, []):
        net = c.get("net", "")
        if net:
            bucket(net)["vias"] += 1

    total = {"length": 0.0, "vias": 0, "pieces": 0}
    for b in per.values():
        total["length"] += b["length"]
        total["vias"] += b["vias"]
        total["pieces"] += b["pieces"]
    per[""] = total
    return per


def load_cell(cicfile, cellname=None):
    opener = gzip.open if str(cicfile).endswith(".gz") else open
    with opener(cicfile, "rt") as f:
        data = json.load(f)
    cells = data.get("cells") or []
    if cellname:
        for c in cells:
            if c.get("name") == cellname:
                return c
        return None
    return cells[-1] if cells else None


def report(cicfile, cellname=None, um=10000, top=12):
    """A human-readable cost report; the last line is the total."""
    cell = load_cell(cicfile, cellname)
    if cell is None:
        return f"no cell {cellname} in {cicfile}"
    per = cell_cost(cell, um)
    total = per.pop("")
    lines = [f"{'net':<22} {'length/um':>10} {'vias':>5} {'pieces':>7}"]
    ranked = sorted(per.items(), key=lambda kv: -kv[1]["length"])
    for net, b in ranked[:top]:
        lines.append(f"{net:<22} {b['length']:>10.2f} {b['vias']:>5} "
                     f"{b['pieces']:>7}")
    if len(ranked) > top:
        lines.append(f"... {len(ranked) - top} more nets")
    lines.append(f"{'TOTAL':<22} {total['length']:>10.2f} "
                 f"{total['vias']:>5} {total['pieces']:>7}")
    return "\n".join(lines)
