"""The route plan: the maze router's conclusions, replayable.

The stack-level router spends its time DECIDING -- track maps and an
A* search per net -- and then hands the drawing to route.py as one
`addConnectivityRoute` command per net. The decision is worth keeping:
this module persists, per (stack, net) and in routing order, the
resolved command and the claims it made, in `<CELL>.routes.yaml`
beside the design. The next build REPLAYS the commands and skips the
search entirely; route.py redraws them under whatever the technology
says today (measured: the search and its track maps were 23.9 s of a
24.1 s build).

A plan is only as good as the placement it was computed against, so
it carries a fingerprint over every instance's name, cell and
position. Any placement change -- a reorder, a resize, a new fill --
invalidates the whole plan and the next build searches again and
rewrites it. Blocked nets are recorded too: replay reproduces the
same outcome, it does not quietly retry what the search proved
impossible.

Delete the file (or set CICPY_NO_ROUTEPLAN=1) to force a fresh
search.
"""
import hashlib
import logging
import os

log = logging.getLogger("RoutePlan")

FORMAT = 1


def plan_path(layout):
    dirname = getattr(layout, "dirname", "") or ""
    name = getattr(layout, "name", "") or ""
    if not dirname or not name:
        return None
    return os.path.join(dirname, name + ".routes.yaml")


def fingerprint(layout):
    """Placement identity: every instance's name, cell and position."""
    rows = []
    for i in layout.iterInstances():
        rows.append((getattr(i, "instanceName", ""),
                     getattr(i, "cell", ""),
                     int(i.x1), int(i.y1)))
    blob = repr(sorted(rows)).encode()
    return hashlib.sha1(blob).hexdigest()


def load_plan(layout):
    """The stored plan as {(stack, net): entry} in order, or None.

    None when there is no file, the fingerprint does not match the
    placement, or replay is disabled.
    """
    if os.environ.get("CICPY_NO_ROUTEPLAN"):
        return None
    path = plan_path(layout)
    if path is None or not os.path.exists(path):
        return None
    import yaml
    try:
        with open(path) as f:
            doc = yaml.safe_load(f) or {}
    except Exception as e:
        log.warning(f"{path}: unreadable route plan: {e}")
        return None
    if doc.get("format") != FORMAT:
        log.info(f"{path}: route plan format {doc.get('format')} "
                 f"!= {FORMAT}; searching fresh")
        return None
    if doc.get("fingerprint") != fingerprint(layout):
        log.info(f"{path}: placement changed since the plan was "
                 f"computed; searching fresh")
        return None
    out = {}
    for e in doc.get("routes", []) or []:
        out[(e.get("stack", ""), e.get("net", ""))] = e
    return out


def save_plan(layout, entries, visited_stacks, previous=None):
    """Write the plan: this run's entries, plus the previous plan's
    entries for stacks this run did not visit (an `only` run must not
    clobber the rest)."""
    path = plan_path(layout)
    if path is None or os.environ.get("CICPY_NO_ROUTEPLAN"):
        return
    keep = []
    if previous:
        keep = [e for (stack, _n), e in previous.items()
                if stack not in visited_stacks]
    import yaml
    doc = {"format": FORMAT,
           "fingerprint": fingerprint(layout),
           "routes": keep + entries}
    try:
        with open(path, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False)
    except Exception as e:
        log.warning(f"{path}: could not write route plan: {e}")
        return
    log.info(f"route plan: {len(entries)} entries written to {path}")
