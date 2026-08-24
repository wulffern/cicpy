#!/usr/bin/env python3
"""The output printers, loaded WHEN ASKED FOR.

Importing this package used to import every printer, and through them
every printer's dependencies -- svgwrite alone is ~80 ms -- on every
cicpy invocation, including the ones that print nothing. PEP 562:
`cicpy.printer.SvgPrinter` still works everywhere it worked, and the
module behind a name is imported the first time that name is touched.
"""

_LOCATIONS = {
    "CellInfoPrinter": "cellinfoprinter",
    "DesignPrinter": "designprinter",
    "MagicPrinter": "magicprinter",
    "MinMax": "mcprinter",
    "MinecraftCuts": "mcprinter",
    "MinecraftCellPrinter": "mcprinter",
    "SkillLayPrinter": "skilllayprinter",
    "SkillSchPrinter": "skillschprinter",
    "SpicePrinter": "spiceprinter",
    "SvgCell": "svgprinter",
    "SvgPrinter": "svgprinter",
    "VerilogPrinter": "verilogprinter",
    "XschemSymbol": "xschemprinter",
    "XschemPrinter": "xschemprinter",
}

__all__ = list(_LOCATIONS)


def __getattr__(name):
    modname = _LOCATIONS.get(name)
    if modname is None:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    from importlib import import_module
    mod = import_module("." + modname, __name__)
    value = getattr(mod, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_LOCATIONS))
