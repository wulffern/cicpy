#!/usr/bin/env python3
"""Compile a ciccreator object file into a Design.

This is the port of cIcCore::Design's reading half -- readCells() and
createCell(). The shape of a compile is fixed and every cell goes
through all of it, in this order:

    resolve class (through the inherit chain)  ->  construct
    afterNew    -> instance methods -> subckt
    beforePlace -> place()  -> afterPlace
    beforeRoute -> route()  -> afterRoute -> addAllPorts()
    beforePaint -> paint()  -> afterPaint

Parents run before the cell's own methods at every hook, so a child
overrides what it inherits rather than fighting it.
"""
import logging
import os
import re
import tempfile

from . import dispatch, registry
from .reader import readJson

log = logging.getLogger("cicpy.compiler")

DEFAULT_CLASS = "cIcCore::LayoutCell"


class Compiler():

    def __init__(self, design, includePaths=(), prefix="", keepGoing=False):
        self.design = design
        self.includePaths = list(includePaths)
        self.prefix = prefix
        #- keep compiling after a cell the port cannot build yet, so the
        #- parity harness can score what DOES work instead of stopping at
        #- the first gap. The names are collected, never swallowed.
        self.keepGoing = keepGoing
        self.failed = []
        #- every cell's JSON, by name, so `inherit` and `leech` can find it
        self._json = {}
        self.ignoreSetYoffsetHalf = False
        self.topcells = []
        self.patterns = {}
        self.spice = None

    #- -----------------------------------------------------------------
    #- Reading
    #- -----------------------------------------------------------------

    def read(self, filename):
        """Compile `filename`, and everything it includes, into the design."""
        self.readCells(filename)
        #- Every cut the routing asked for is a CELL, and it has to be in
        #- the design before anything that places it -- Design::read puts
        #- them at the front for exactly that reason.
        self.design.addCuts()
        return self.design

    def readCells(self, filename):
        #- the netlist is the object file's name with .spi in place of
        #- .json; connectivity comes from there, never from the JSON
        self.readSpice(filename)

        log.info("Reading '%s'", filename)
        obj = readJson(filename)

        options = obj.get("options")
        if isinstance(options, dict):
            self.ignoreSetYoffsetHalf = bool(
                options.get("ignoreSetYoffsetHalf", self.ignoreSetYoffsetHalf))
            if "prefix" in options:
                self.prefix = options["prefix"]
            for v in options.get("topcells", []) or []:
                self.topcells.append(v)

        patterns = obj.get("patterns")
        if isinstance(patterns, dict):
            for key, val in patterns.items():
                if isinstance(val, list):
                    self.patterns[key] = [str(v) for v in val]

        for libfile in obj.get("library", []) or []:
            path = self.find(libfile, filename)
            if path is None:
                raise FileNotFoundError("Could not find library '%s'" % libfile)
            log.info("Reading library '%s'", path)
            self.readCells(path)

        for incfile in obj.get("include", []) or []:
            path = self.find(incfile, filename)
            if path is None:
                raise FileNotFoundError("Could not find include '%s'" % incfile)
            self.readCells(path)

        cells = obj.get("cells")
        if not isinstance(cells, list):
            raise ValueError("Could not find 'cells' array in %s" % filename)

        for c in cells:
            if not isinstance(c, dict):
                continue
            name = c.get("name", "")
            if name:
                self._json[name] = c
            try:
                self.createCell(c)
            except NotImplementedError as e:
                if not self.keepGoing:
                    raise
                self.failed.append((name, str(e)))
                log.warning("skipping '%s': %s", name, e)

        return True

    def find(self, name, relativeTo):
        """Search the include paths, then the referring file's directory."""
        if os.path.exists(name):
            return name
        here = os.path.dirname(os.path.abspath(relativeTo))
        for base in list(self.includePaths) + [here]:
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
        return None

    def readSpice(self, filename):
        spifile = filename[:-len(".json")] + ".spi" if filename.endswith(".json") \
            else filename + ".spi"
        if not os.path.exists(spifile):
            return
        try:
            import cicspi
            if self.spice is None:
                self.spice = cicspi.SpiceParser()
            self.spice.parseFile(spifile)
        except ImportError:
            log.warning("cicspi not installed, no connectivity from %s", spifile)

    #- -----------------------------------------------------------------
    #- Building one cell
    #- -----------------------------------------------------------------

    def findAllParents(self, inherit, out):
        """The inherit chain, OUTERMOST FIRST, so a child overrides it."""
        par = self._json.get(inherit)
        if par is None:
            return
        if "inherit" in par:
            self.findAllParents(par["inherit"], out)
        out.append(par)

    def resolveClass(self, jobj, parents):
        cl = jobj.get("class", "")
        #- a class named anywhere up the chain wins over the child's own,
        #- matching createCell: the loop runs forward and keeps the LAST
        #- parent that named one
        if "class" in jobj and parents:
            for par in parents:
                if "class" in par:
                    cl = par["class"]
        return cl or DEFAULT_CLASS

    def createCell(self, jobj):
        name = jobj.get("name", "")
        if not name:
            if "comment" not in jobj:
                log.error("Cell with no name and no class")
            return None

        parents = []
        if "inherit" in jobj:
            self.findAllParents(jobj["inherit"], parents)

        #- `leech` borrows another cell's methods without being it
        leech = jobj.get("leech")
        if leech and leech in self._json:
            parents.append(self._json[leech])

        cl = self.resolveClass(jobj, parents)
        cls = registry.get(cl)
        if cls is None:
            log.error("did not find class '%s' for cell '%s'", cl, name)
            return None

        cell = cls()
        cell.name = self.prefix + name
        cell.design = self.design
        #- placement resolves child cells through the parent design
        cell.parent = self.design
        cell.prefix = self.prefix
        cell.obj = jobj
        if self.patterns:
            cell.patterns = self.patterns

        kw = dict(ignoreSetYoffsetHalf=self.ignoreSetYoffsetHalf)

        dispatch.runAllParents("afterNew", cell, parents, fromParent=True, **kw)
        dispatch.runAll("afterNew", cell, jobj, **kw)

        for par in parents:
            dispatch.runIfObjectCan(cell, par, fromParent=True, **kw)
        dispatch.runIfObjectCan(cell, jobj, **kw)

        self.attachSubckt(cell, jobj, parents, name)

        self.hook("Place", cell, jobj, parents, kw)
        self.hook("Route", cell, jobj, parents, kw)
        if hasattr(cell, "addAllPorts"):
            cell.addAllPorts()
        self.hook("Paint", cell, jobj, parents, kw)

        self.design.add(cell)
        return cell

    def hook(self, stage, cell, jobj, parents, kw):
        """before<Stage> -> <stage>() -> after<Stage>."""
        dispatch.runAllParents("before" + stage, cell, parents, fromParent=True, **kw)
        dispatch.runAll("before" + stage, cell, jobj, **kw)
        fn = getattr(cell, stage.lower(), None)
        if callable(fn):
            fn()
        dispatch.runAllParents("after" + stage, cell, parents, fromParent=True, **kw)
        dispatch.runAll("after" + stage, cell, jobj, **kw)

    def attachSubckt(self, cell, jobj, parents, name):
        """Give the cell its connectivity.

        Three places a subckt can come from, in ciccreator's order:

          1. the companion .spi, by the cell's own name
          2. a `spice` array in the object file -- a netlist written
             INLINE, which is how the route demos describe a cell that
             exists only to be routed and has no .spi of its own
          3. the nearest parent that has one, renamed to this cell, so
             a cell built by `inherit` gets the devices it places

        Without (2) such a cell has no nodes, addAllPorts finds nothing
        to publish, and the cell comes out with no ports at all.
        """
        if self.spice is None:
            return
        ckt = self.spice.get(name)

        if ckt is None and isinstance(jobj.get("spice"), list):
            lines = [str(v) for v in jobj["spice"]]
            ckt = self.parseInlineSpice(self.applySpiceRegex(lines, jobj), name)

        if ckt is None:
            for par in reversed(parents):
                ckt = self.spice.get(par.get("name", ""))
                if ckt is not None:
                    break

        if ckt is not None:
            cell.ckt = ckt
            cell.subckt = ckt

    def applySpiceRegex(self, lines, jobj):
        """`spiceRegex` rewrites the netlist before it is parsed."""
        for rule in jobj.get("spiceRegex", []) or []:
            if not isinstance(rule, list) or len(rule) < 2:
                continue
            frm, to = str(rule[0]), str(rule[1])
            lines = [re.sub(frm, to, ln) for ln in lines]
        return lines

    def parseInlineSpice(self, lines, name):
        """Parse netlist lines with the real parser, via a temp file.

        cicspi only parses files. Reimplementing .subckt parsing here
        to avoid a temp file would mean a second, subtly different
        netlist parser in the same package -- worse than the file.
        """
        with tempfile.NamedTemporaryFile("w", suffix=".spi", delete=False) as fo:
            fo.write("\n".join(lines) + "\n")
            path = fo.name
        try:
            self.spice.parseFile(path)
        except Exception as e:
            log.error("%s: could not parse inline spice: %s", name, e)
            return None
        finally:
            os.unlink(path)
        return self.spice.get(name)
