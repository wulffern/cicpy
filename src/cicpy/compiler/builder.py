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

#- Design::Design()'s cellTranslator, verbatim: the names object files
#- write are marketing names for a smaller set of classes. Notably
#- Layout::LayoutDigitalCell IS cIcCore::LayoutCell -- it never grew
#- behaviour of its own.
CELL_TRANSLATOR = {
    "Gds::GdsPatternTransistor": "cIcCore::PatternTransistor",
    "Gds::GdsPatternHighResistor": "cIcCore::PatternHighResistor",
    "Gds::GdsPatternResistor": "cIcCore::PatternResistor",
    "Gds::GdsPatternCapacitor": "cIcCore::PatternCapacitor",
    "Gds::GdsPatternCapacitorGnd": "cIcCore::PatternCapacitor",
    "Layout::LayoutDigitalCell": "cIcCore::LayoutCell",
    "LayoutCell": "cIcCore::LayoutCell",
    "Layout::LayoutRotateCell": "cIcCore::LayoutRotateCell",
    "Layout::LayoutSARCDAC": "cIcCells::SAR",
    "Layout::LayoutCDACSmall": "cIcCells::CDAC",
    "Layout::LayoutCapCellSmall": "cIcCells::CapCell",
}


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
        #- ONE subckt table for the whole compile, like the reference's
        #- global registry: library imports fill it first, and a local
        #- netlist parsed later OVERWRITES a library definition. Two
        #- dicts here meant the library's node order won -- sun_pll's
        #- RPPO8 got its N and P pins swapped and both LPF resistors
        #- routed mirror-image.
        self.spice = None
        try:
            import cicspi
            self.spice = cicspi.SpiceParser()
            if cicspi.Subckt.circuits is None:
                cicspi.Subckt.circuits = self.spice
        except ImportError:
            pass

    #- -----------------------------------------------------------------
    #- Reading
    #- -----------------------------------------------------------------

    def read(self, filename):
        """Compile `filename`, and everything it includes, into the design."""
        from ..core.route import Route
        prev = Route.compat
        Route.compat = "ciccreator"
        try:
            self.readCells(filename)
        finally:
            Route.compat = prev
        #- Every cut the routing asked for is a CELL, and it has to be in
        #- the design before anything that places it -- Design::read puts
        #- them at the front for exactly that reason.
        self.design.addCuts()
        #- Design::read: options.topcells mark the used set, walking
        #- every instance so the writer can drop what nothing reaches
        for name in self.topcells:
            self._markUsed(self.design.cells.get(name), set())
        return self.design

    def _markUsed(self, cell, seen):
        """Cell::updateUsedChildren: recurse the child tree, and follow
        every instance to the design cell it places."""
        if cell is None or id(cell) in seen:
            return
        seen.add(id(cell))
        cell.cellUsed = True
        for ch in list(getattr(cell, "children", []) or []):
            if ch is None:
                continue
            sub = getattr(ch, "_cell_obj", None)
            if sub is None:
                cn = getattr(ch, "cell", None)
                if isinstance(cn, str) and cn:
                    sub = self.design.cells.get(cn)
            if sub is not None:
                self._markUsed(sub, seen)
            if hasattr(ch, "children"):
                self._markUsed(ch, seen)

    #- these serialize their raw name; everything else gets the prefix
    #- (Cell::toJson: isText/isPort/isRoute keep name() -- a RouteRing
    #- is NOT isRoute, and a nameless Guard really does emit "<prefix>")
    _RAW_NAME_CLASSES = frozenset(("Rect", "Port", "Text", "cIcCore::Route"))

    def toJson(self):
        """The design as .cic JSON, with options.prefix and topcells
        applied the way Design::toJson applies them: unused cells are
        dropped when topcells is set, and the prefix lands on names at
        write time, never during the build."""
        obj = self.design.toJson()
        if self.topcells:
            used = {n for n, c in self.design.cells.items()
                    if getattr(c, "cellUsed", False)}
            obj["cells"] = [c for c in obj["cells"] if c.get("name") in used]
        if self.prefix:
            for c in obj["cells"]:
                self._prefixJson(c)
        return obj

    def _prefixJson(self, o):
        p = self.prefix
        if o.get("class", "") not in Compiler._RAW_NAME_CLASSES and "name" in o:
            o["name"] = p + (o.get("name") or "")
        if isinstance(o.get("cell"), str):
            o["cell"] = p + o["cell"]
        ckt = o.get("ckt")
        if isinstance(ckt, dict):
            if "name" in ckt:
                ckt["name"] = p + (ckt.get("name") or "")
            for i in ckt.get("instances") or []:
                if isinstance(i, dict) and "subcktName" in i:
                    i["subcktName"] = p + (i.get("subcktName") or "")
        si = o.get("subcktInstance")
        if isinstance(si, dict) and "subcktName" in si:
            si["subcktName"] = p + (si.get("subcktName") or "")
        for c in o.get("children") or []:
            if isinstance(c, dict):
                self._prefixJson(c)

    def readLibrary(self, path):
        """A `library` entry is a SERIALIZED design -- a .cic another
        compile already wrote -- so it deserializes straight into cells
        (Design::readJsonFile -> fromJson); only `include` compiles.
        The library's subckts go into the spice registry so this
        design's netlists can instantiate its cells by name.
        """
        import re as _re
        before = set(self.design.cells)
        self.design.fromJsonFile(path)
        libpath = _re.sub(r"\.cic(\.gz)?$", "", path)
        for name, cell in self.design.cells.items():
            if name in before:
                continue
            if not getattr(cell, "libpath", ""):
                cell.libpath = libpath
            #- the reference resurrects each library cell as its REAL
            #- class (Qt metatype), so a Pattern* cell's closing
            #- updateBoundingRect reruns the pattern FORMULA -- which
            #- is what wrote the file's box. Reading children as plain
            #- geometry unions in the well enclosures instead; put the
            #- file's box back.
            jo = self.design.jcells.get(name) or {}
            bb = getattr(cell, "cic_bbox", None)
            if bb and "Pattern" in str(jo.get("class", "")):
                cell.x1, cell.y1, cell.x2, cell.y2 = bb
            ckt = getattr(cell, "ckt", None)
            if ckt is not None:
                import cicspi
                if self.spice is not None and name not in self.spice:
                    self.spice[name] = ckt
                if cicspi.Subckt.circuits is None:
                    cicspi.Subckt.circuits = self.spice if self.spice is not None else {}
                if name not in cicspi.Subckt.circuits:
                    cicspi.Subckt.circuits[name] = ckt

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
            self.readLibrary(path)

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
            for ckt in self.spice.values():
                self.expandMultipliers(ckt)
        except ImportError:
            log.warning("cicspi not installed, no connectivity from %s", spifile)

    _M_RE = re.compile(r"\bM\s*=\s*(\d+)", re.I)

    def expandMultipliers(self, ckt):
        """XCAPB ... M=7 is SEVEN instances: XCAPB0 .. XCAPB6.

        ciccreator's parser expands the multiplier as it reads
        (subckt.cpp: 'Make paralell devices'); cicspi drops parameters
        on the floor, so the expansion happens here, from the line the
        instance still carries. The clones stay contiguous, which is
        what stacks them into one column at place()."""
        import cicspi
        instances = getattr(ckt, "instances", None)
        if not instances:
            return
        out = []
        for inst in instances:
            line = getattr(inst, "spiceStr", "") or ""
            self._applyLineProperties(inst, line)
            m = self._M_RE.search(line)
            if not m or not str(getattr(inst, "name", "")).upper().startswith("X"):
                out.append(inst)
                continue
            count = int(m.group(1))
            base = inst.name
            inst.name = base + "0"
            out.append(inst)
            for i in range(1, count):
                clone = cicspi.SubcktInstance()
                #- parse() resolves the model name through the parser
                clone.parser = getattr(inst, "parser", None)
                clone.parent = getattr(inst, "parent", None)
                clone.parse(line, getattr(inst, "lineNumber", 0))
                clone.name = "%s%d" % (base, i)
                self._applyLineProperties(clone, line)
                out.append(clone)
        ckt.instances = out

    _PROP_RE = re.compile(r"([A-Za-z_]\w*)\s*=\s*(\S+)")

    def _applyLineProperties(self, inst, line):
        """xoffset=4 on a netlist line is an instance PROPERTY, and
        place() reads it (C++ ckt_inst->hasProperty). cicspi keeps only
        the raw line, so lift every k=v off it."""
        if not line:
            return
        try:
            props = inst.properties
        except AttributeError:
            return
        for m in Compiler._PROP_RE.finditer(line):
            props.setdefault(m.group(1), m.group(2))

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
        """The nearest ancestor that names a class decides.

        The C++ source guards this on the CHILD having a class of its
        own, but the binary demonstrably does not behave that way:
        NCHDL declares none, inherits DMOSE, and both the console and
        the golden .cic build it as a PatternTransistor. Observed
        behaviour outranks the text, so the walk is unconditional --
        outermost parent first, the last (nearest) one with a class
        wins, over the child's own too.
        """
        cl = jobj.get("class", "")
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
        cl = CELL_TRANSLATOR.get(cl, cl)
        cls = registry.get(cl)
        if cls is None:
            log.error("did not find class '%s' for cell '%s'", cl, name)
            return None

        cell = cls()
        #- names stay UNPREFIXED while the design builds: the reference
        #- applies options.prefix at serialization (Design::toJson sets
        #- it on each cell as it writes), so netlists, inherit chains
        #- and instance lookups all resolve raw names. Prefixing here
        #- broke every cross-file lookup the moment ip.json set one.
        cell.name = name
        cell.design = self.design
        #- placement resolves child cells through the parent design
        cell.parent = self.design
        cell.prefix = self.prefix
        cell.obj = jobj
        if self.patterns:
            cell.patterns = self.patterns

        kw = dict(ignoreSetYoffsetHalf=self.ignoreSetYoffsetHalf)

        #- "decorator": lifecycle hooks that ride along with the cell's
        #- own methods (C++ LayoutCellDecorator)
        decorators = []
        from .decorators import DECORATORS
        for entry in jobj.get("decorator") or []:
            if not isinstance(entry, dict) or not entry:
                continue
            dname = next(iter(entry))
            dcls = DECORATORS.get(dname)
            if dcls is None:
                log.error("%s: unknown decorator '%s'", name, dname)
                continue
            d = dcls()
            d.setCell(cell)
            d.setOptions(entry[dname])
            decorators.append(d)

        def runDecorators(stage):
            for d in decorators:
                getattr(d, stage)()

        dispatch.runAllParents("afterNew", cell, parents, fromParent=True, **kw)
        dispatch.runAll("afterNew", cell, jobj, **kw)
        runDecorators("afterNew")

        for par in parents:
            dispatch.runIfObjectCan(cell, par, fromParent=True, **kw)
        dispatch.runIfObjectCan(cell, jobj, **kw)

        self.attachSubckt(cell, jobj, parents, name)

        #- every reference cell HAS a subckt, netlist or not: a plain
        #- tile with no electrical view still writes ckt{name, nodes:[]}
        #- to the .cic, and the xschem transpiler dereferences it --
        #- ckt:{} read back as None crashed on the first tap cell
        if getattr(cell, "ckt", None) is None:
            try:
                import cicspi
                empty = cicspi.Subckt()
                empty.name = cell.name
                cell.ckt = empty
                cell.subckt = empty
            except ImportError:
                pass

        self.hook("Place", cell, jobj, parents, kw, decorators)
        self.hook("Route", cell, jobj, parents, kw, decorators)
        if hasattr(cell, "addAllPorts"):
            cell.addAllPorts()
        self.hook("Paint", cell, jobj, parents, kw, decorators)

        self.design.add(cell)
        self.registerSubckt(cell)
        return cell

    def registerSubckt(self, cell):
        """Put the cell's subckt where instances can FIND it.

        The C++ ends createCell with `ckt->addSubckt()` -- without it a
        pattern device's constructed subckt exists only on the cell,
        Subckt.getSubckt(name) answers None, and setSubcktInstance
        builds no instance ports: every standard cell placed its
        transistors and lost their pins.
        """
        import cicspi
        #- either attribute: attachSubckt sets both, but a cell whose
        #- netlist came from a parseSubckt block only has .ckt
        ckt = getattr(cell, "subckt", None) or getattr(cell, "ckt", None)
        if ckt is None:
            return
        try:
            ckt.name = cell.name
        except Exception:
            pass
        if self.spice is not None and cell.name not in self.spice:
            self.spice[cell.name] = ckt
        if cicspi.Subckt.circuits is None:
            cicspi.Subckt.circuits = self.spice if self.spice is not None else {}
        if cell.name not in cicspi.Subckt.circuits:
            cicspi.Subckt.circuits[cell.name] = ckt

    def hook(self, stage, cell, jobj, parents, kw, decorators=()):
        """before<Stage> -> <stage>() -> after<Stage>.

        Decorators ride along in the reference's exact order: their
        before<Stage> runs after the cell's before methods; their
        <stage>() runs right after the cell's -- but only Place and
        Paint have that call, Route does not; their after<Stage> runs
        after the cell's after methods.
        """
        def deco(hookname):
            for d in decorators:
                getattr(d, hookname)()

        dispatch.runAllParents("before" + stage, cell, parents, fromParent=True, **kw)
        dispatch.runAll("before" + stage, cell, jobj, **kw)
        deco("before" + stage)
        fn = getattr(cell, stage.lower(), None)
        if callable(fn):
            fn()
        if stage in ("Place", "Paint"):
            deco(stage.lower())
        dispatch.runAllParents("after" + stage, cell, parents, fromParent=True, **kw)
        dispatch.runAll("after" + stage, cell, jobj, **kw)
        deco("after" + stage)

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
        #- no companion .spi yet does NOT mean no connectivity: an
        #- inline `spice` array still needs parsing, so make sure the
        #- parser exists before any lookup
        if self.spice is None:
            import cicspi
            self.spice = cicspi.SpiceParser()
        ckt = self.spice.get(name)

        if ckt is None and isinstance(jobj.get("spice"), list):
            lines = [str(v) for v in jobj["spice"]]
            ckt = self.parseInlineSpice(self.applySpiceRegex(lines, jobj), name)

        #- a pattern device CONSTRUCTED its subckt: the measured Mosfet
        #- or resistor lives in ckt.devices, and the reference keeps it
        #- (no netlist names the cell, so nothing overrides). Deriving
        #- one from a parent's netlist here replaced the device with an
        #- empty body and the transpiled spice lost the transistor.
        own = getattr(cell, "subckt", None)
        if ckt is None and own is not None and getattr(own, "devices", None):
            return

        if ckt is None:
            #- inherit the NEAREST parent's netlist, REPARSED under this
            #- cell's name -- not shared: SARDIGEX4 is SARDIGEX2's
            #- netlist with a spiceRegex swapping every SWX2 for SWX4,
            #- and rewriting a shared object would rewrite the parent
            for par in reversed(parents):
                pname = par.get("name", "")
                pckt = self.spice.get(pname)
                if pckt is None:
                    continue
                lines = self.subcktLines(pckt, pname)
                lines = [ln.replace(pname, name) for ln in lines]
                ckt = self.parseInlineSpice(lines, name)
                if ckt is not None:
                    break

        #- spiceRegex rewrites the netlist a found subckt describes
        if ckt is not None and jobj.get("spiceRegex") and "spice" not in jobj:
            lines = self.applySpiceRegex(self.subcktLines(ckt, name), jobj)
            reparsed = self.parseInlineSpice(lines, name)
            if reparsed is not None:
                ckt = reparsed

        if ckt is not None:
            cell.ckt = ckt
            cell.subckt = ckt

    def subcktLines(self, ckt, name):
        """The subckt as lines, in the RAW instance order.

        tospice() emits instances in index order, and the raw order is
        the floorplan -- so rebuild from each instance's own line. An
        M-expanded clone carries its source line; keep ONE line per
        source so the reparse expands it again rather than 7 times 7.
        """
        lines = [".subckt %s %s" % (name, " ".join(ckt.nodes))]
        seen = set()
        for inst in ckt.instances:
            ln = getattr(inst, "spiceStr", "") or ""
            if ln and ln not in seen:
                seen.add(ln)
                lines.append(ln)
        lines.append(".ends")
        return lines

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
        ckt = self.spice.get(name)
        if ckt is not None:
            self.expandMultipliers(ckt)
        return ckt
