#!/usr/bin/env python3
"""Which Python class an object file's `class` string names.

ciccreator resolves the string through Qt's metatype system, so the
names carry their C++ namespaces -- `cIcCore::LayoutCell`,
`Layout::LayoutDigitalCell`, `Gds::GdsPatternTransistor`. Object files
in the wild are written against those exact strings, so they stay the
public names here even though nothing in Python needs a namespace.
"""
import logging

log = logging.getLogger("cicpy.compiler")

_CLASSES = {}


def register(name, cls):
    _CLASSES[name] = cls
    return cls


def cicclass(*names):
    """Decorator: register a cell class under its ciccreator name(s)."""
    def deco(cls):
        for n in names:
            register(n, cls)
        return cls
    return deco


def get(name):
    return _CLASSES.get(name)


def known():
    return sorted(_CLASSES)
