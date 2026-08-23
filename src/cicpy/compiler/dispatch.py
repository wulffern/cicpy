#!/usr/bin/env python3
"""Run the methods an object file names, on the cell it names them for.

ciccreator drives layout by REFLECTION: a key in a cell's JSON object
is the name of a method to call on the C++ object, and the value is
its argument. Qt needs moc and Q_INVOKABLE to make that possible.
Python needs getattr, so the whole mechanism is this file.

Three rules decide what a key means, and they are checked in the same
order Design::runIfObjectCanMethods checks them:

  1. a method of that name            -> call it with the value
  2. key ends in "s" and the singular -> call the singular once per
     names a method                      element of the array
  3. an attribute of that name        -> assign the value

Anything else is an error the object file's author needs to see, with
the two exceptions ciccreator carves out for keys that only ever meant
something to the SKILL backend.
"""
import inspect
import logging
import re

log = logging.getLogger("cicpy.compiler")

#- Keys that are structure, not method calls. Copied deliberately from
#- design.cpp: only `new` is anchored there, so `inherit`/`class`/... are
#- substring tests, and a key CONTAINING one of them is skipped too.
RESERVED = re.compile(
    r"^new|inherit|leech|class|name|before.*|after.*|comment|decorator|spiceRegex")

#- Keys that belonged to backends this tool no longer has. Silently
#- ignored so an object file written for the SKILL flow still compiles.
#- `spice` is here for a different reason: it IS read, by the compiler's
#- own attachSubckt, as the cell's inline netlist -- it was never a
#- method for the dispatcher to find.
IGNORED = ("symbol", "rows", "composite", "comment", "description", "spice")


def arity(fn):
    """(required positional count, takes *args) for a bound method.

    mirrorCenterX/mirrorCenterY take no argument. Qt used to drop the
    extra one quietly and newer Qt refuses the call outright, which
    left cells unmirrored -- ciccreator now asks the method how many
    parameters it wants. Ask the same question of a Python method.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return 1, True
    required, star = 0, False
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            star = True
            continue
        if p.default is p.empty:
            required += 1
    return required, star


def call(cell, fn, value):
    """Invoke one method with the JSON value as its argument.

    Every ciccreator method takes a single QJsonArray/QJsonObject and
    unpacks it itself, so the C++ marshalling is one argument or none.
    cicpy's own methods were written for Python and take the pieces
    UNPACKED -- addDirectedRoute(layer, net, route, options) against
    the object file's ["M2","A","-|","..."]. Both are the same call
    with the parentheses in a different place, so spread a list into a
    method that asks for more than one argument and hand it over whole
    to a method that asks for one.
    """
    required, star = arity(fn)
    if required == 0 and not star:
        fn()
    elif required > 1 and isinstance(value, list):
        fn(*value)
    else:
        fn(value)


def runIfObjectCan(cell, jobj, theme="", fromParent=False, ignoreSetYoffsetHalf=False):
    """Apply every method-like key in `jobj` to `cell`."""
    for key, value in jobj.items():
        if RESERVED.search(key):
            continue
        if ignoreSetYoffsetHalf and key == "setYoffsetHalf":
            continue
        #- `abstract` marks the cell that DECLARES it as a template not to
        #- be written out. Cells inheriting from it are real, so the flag
        #- must not travel down the inheritance chain.
        if fromParent and key == "abstract":
            continue

        member = getattr(cell, key, None)

        if callable(member):
            call(cell, member, value)
            continue

        #- an array key whose singular names a method: run it per element
        if key.endswith("s"):
            singular = getattr(cell, key[:-1], None)
            if callable(singular):
                if isinstance(value, list):
                    for v in value:
                        call(cell, singular, v)
                else:
                    call(cell, singular, value)
                continue

        #- a plain attribute is a property assignment
        if member is not None or hasattr(cell, key):
            setattr(cell, key, value)
            continue

        if key not in IGNORED:
            log.error("%s: no method or property '%s'%s",
                      jobj.get("name", getattr(cell, "name", "?")), key,
                      " (%s)" % theme if theme else "")


def runAll(name, cell, jobj, **kw):
    """Run a lifecycle hook: `jobj[name]` is an object or a list of them."""
    jo = jobj.get(name)
    if jo is None:
        return
    cellname = jobj.get("name", "")
    if isinstance(jo, dict):
        job = dict(jo)
        job["name"] = cellname
        runIfObjectCan(cell, job, theme=name, **kw)
    elif isinstance(jo, list):
        for entry in jo:
            if not isinstance(entry, dict):
                continue
            job = dict(entry)
            job["name"] = cellname
            runIfObjectCan(cell, job, theme=name, **kw)


def runAllParents(name, cell, parents, **kw):
    for par in parents:
        runAll(name, cell, par, **kw)
