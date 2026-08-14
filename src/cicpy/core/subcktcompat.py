"""Reaching into a Subckt without depending on an unreleased cicspi.

`Subckt.getInstance` exists in cicspi's working tree and NOT in any
release -- 0.1.4, the newest on PyPI, has `addInstance` and
`getInstances` but no singular getter. cicpy called it from two places
in its own source, so a cicpy installed beside a released cicspi
raised AttributeError at runtime and CI failed on the API rather than
on anything it was testing.

Use the real method when it is there; otherwise ask for the same thing
the way the release can answer.
"""


def instance_of(ckt, name):
    """The instance called `name` in `ckt`, or None."""
    if ckt is None or not name:
        return None
    get = getattr(ckt, "getInstance", None)
    if callable(get):
        try:
            return get(name)
        except Exception:
            return None
    for inst in (getattr(ckt, "instances", []) or []):
        if getattr(inst, "name", None) == name:
            return inst
    return None
