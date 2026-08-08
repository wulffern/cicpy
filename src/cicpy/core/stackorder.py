"""Which columns are worth reordering, and what it would buy.

A rail down a column of parallel devices crosses every pin it passes,
so a net whose pins on that terminal are interleaved with another net's
cannot have one. That is decided by the order the devices sit in, which
is placement's business, not routing's -- and it is cheap to fix and
expensive to discover. A load column measured in the wild came out

    A A A A B A

and the one odd device in the middle is the difference between five
pins on a rail and five pins going up a layer and back.

Finding that by drawing it costs a regeneration per column and reads as
a short or an open with no hint of the cause. This reads the netlist
instead and says, per column: what the terminal carries, whether it is
interleaved, and what regrouping would make railable. It needs no
placement, so it can be asked before the first one.
"""

import re
from collections import OrderedDict

#- D G S B, the terminal order of a four terminal device
TERMINALS = ("D", "G", "S", "B")
#- the group of an instance is its leading letters, xbl0<2> -> xbl
GROUP_RE = re.compile(r"^(x\D+)")


def _contiguous(seq):
    """True if every value's occurrences are in one unbroken run."""
    seen, last = set(), None
    for v in seq:
        if v != last and v in seen:
            return False
        seen.add(v)
        last = v
    return True


def analyse(subckt, terminal="D", groups=None):
    """Per column: the terminal's nets, in order, and what regrouping buys."""
    try:
        index = TERMINALS.index(terminal.upper())
    except ValueError:
        raise ValueError(f"terminal must be one of {', '.join(TERMINALS)}")

    columns = OrderedDict()
    for inst in getattr(subckt, "instances", []):
        nodes = getattr(inst, "nodes", None)
        if not nodes or len(nodes) <= index:
            continue
        match = GROUP_RE.match(getattr(inst, "name", ""))
        if not match:
            continue
        name = match.group(1)
        if groups and name not in groups:
            continue
        columns.setdefault(name, []).append((inst.name, nodes[index]))

    out = []
    for name, members in columns.items():
        nets = [net for _, net in members]
        counts = OrderedDict()
        for net in nets:
            counts[net] = counts.get(net, 0) + 1
        #- a net can be railed if it has more than one pin here. Whether
        #- it *may* be is the contiguity question
        railable = [net for net, n in counts.items() if n > 1]
        out.append({
            "column": name,
            "terminal": terminal.upper(),
            "instances": [inst for inst, _ in members],
            "nets": nets,
            "counts": counts,
            "contiguous": _contiguous(nets),
            "railable": railable,
            #- every net is contiguous after a stable group-by, so this
            #- is exactly what orderByTerminalNet would make possible
            "railable_after_reorder": railable,
            "blocked": [] if _contiguous(nets) else railable,
        })
    return out


def report(rows, verbose=False):
    lines = []
    for row in rows:
        counts = ", ".join(f"{net}x{n}" for net, n in row["counts"].items())
        lines.append(f"{row['column']}  {row['terminal']}: {counts}")
        lines.append("   " + " ".join(row["nets"]))
        if not row["railable"]:
            lines.append("   no net has two pins here, nothing to rail")
        elif row["contiguous"]:
            lines.append(
                "   already grouped, rails available: "
                + ", ".join(row["railable"]))
        else:
            lines.append(
                "   INTERLEAVED, reorder would free rails on: "
                + ", ".join(row["blocked"]))
        if verbose:
            lines.append("   " + " ".join(row["instances"]))
    if not lines:
        return "no columns found"
    lines.append("")
    lines.append("orderByTerminalNet(<terminal>) on a stack regroups it. Not on a")
    lines.append("series chain, where the order makes each link a neighbour, and")
    lines.append("not on a matched pair, where the order is the matching.")
    return "\n".join(lines)
