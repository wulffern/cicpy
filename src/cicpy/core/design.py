######################################################################
##          <carsten@wulff.no>
## ###################################################################
## Created       : wulff at 2020-3-14
## ###################################################################
##  The MIT License (MIT)
## 
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
## 
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
## 
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##  
######################################################################

from .rect import Rect
from .cell import Cell
from .layoutcell import LayoutCell

import cicpy as cic

import os
import gzip
import json
import re
import logging
import glob

class Design():

    def __init__(self):
        self.cells = dict()
        self.cellnames = list()
        self.jcells = dict()
        self.log = logging.getLogger("DesignPrinter")
        self.prefix = ""
        self.primitiveProviders = []
        self.layoutcell_factories = dict()

    def registerLayoutCellClass(self, name, factory):
        """For this cell name, instantiate this instead of LayoutCell.

        `factory` is any zero-argument callable returning the cell --
        the class itself, or a closure carrying constructor arguments.
        The framework builds the top cell wherever a netlist is read
        (see MagicDesign.readFromSpice), so a cell that needs its own
        LayoutCell subclass -- a SidecarCell that builds its own
        subcells, say -- registers here before the read.
        """
        self.layoutcell_factories[name] = factory

    def newLayoutCell(self, name):
        return self.layoutcell_factories.get(name, LayoutCell)()


    def addCuts(self):
        # Import all cuts and add them to the design (matching C++ behavior)
        from .cut import Cut
        for cut in Cut.getCuts():
            if cut.name not in self.cells:
                print(f"Adding cut {cut.name}")
                self.cells[cut.name] = cut
                self.cellnames.insert(0, cut.name)  # Add at the beginning like C++

    def _readJsonFile(self, fname):
        jobj = None

        if(fname.endswith(".gz")):
            with gzip.open(fname,"r") as f:
                jobj = json.load(f)
        else:
            with open(fname,"r") as f:
                jobj = json.load(f)

        if(jobj is None):
            import logging
            log = logging.getLogger("Design")
            log.error(f"Could not read {fname}, unrecognized format")
            raise Exception("Could not read %s, unrecognized format" % fname)

        return jobj

    def fromJsonFile(self,fname):
        jobj = self._readJsonFile(fname)

        for o in jobj["cells"]:
            if("class" in o):
                if(o["class"] == "cIcCore::Cell"):
                    c = LayoutCell()
                else:
                    c = LayoutCell()

            c.design = self
            c.fromJson(o)
            self.cells[c.name] = c
            self.jcells[c.name] = o
            self.cellnames.append(c.name)

    def fromJsonFiles(self, *fnames):
        for fname in fnames:
            if not fname:
                continue
            for expanded in sorted(glob.glob(fname)) or [fname]:
                jobj = self._readJsonFile(expanded)
                for o in jobj["cells"]:
                    cname = o.get("name")
                    if not cname:
                        continue

                    if("class" in o):
                        if(o["class"] == "cIcCore::Cell"):
                            c = LayoutCell()
                        else:
                            c = LayoutCell()

                    c.design = self
                    c.fromJson(o)
                    self.cells[c.name] = c
                    self.jcells[c.name] = o
                    if c.name not in self.cellnames:
                        self.cellnames.append(c.name)

    def fromJsonFilesWithDependencies(self, cicfile, includes=()):
        """Load cicfile plus explicit includes, then same-folder cells as needed.

        Sibling .cic/.cic.gz files are indexed by cell name and loaded only when
        an instance in the current design references a missing cell.
        """
        self.fromJsonFiles(*(includes or ()), cicfile)
        siblings = self._indexSiblingCicFiles(cicfile)
        loaded = {os.path.abspath(cicfile)}
        for include in includes or ():
            for expanded in sorted(glob.glob(include)) or [include]:
                loaded.add(os.path.abspath(expanded))

        while True:
            missing = sorted(self._missingInstanceCells())
            pending = [
                siblings[name]
                for name in missing
                if name in siblings and os.path.abspath(siblings[name]) not in loaded
            ]
            if not pending:
                break
            for fname in sorted(set(pending)):
                self.fromJsonFiles(fname)
                loaded.add(os.path.abspath(fname))

        #- ...and the library cells, which are .mag and not .cic
        self.loadMissingFromLibraries(cicfile)

    def _indexSiblingCicFiles(self, cicfile):
        cicfile = os.path.abspath(cicfile)
        root = os.path.dirname(cicfile)
        index = {}
        for pattern in ("*.cic", "*.cic.gz"):
            for fname in sorted(glob.glob(os.path.join(root, pattern))):
                if os.path.abspath(fname) == cicfile:
                    continue
                jobj = self._readJsonFile(fname)
                for cell in jobj.get("cells", []):
                    name = cell.get("name")
                    if name and name not in index:
                        index[name] = fname
        return index

    def _missingInstanceCells(self):
        refs = set()
        for cell in self.cells.values():
            self._collectInstanceCells(cell, refs)
        return refs - set(self.cells.keys())

    def _collectInstanceCells(self, obj, refs, libs=None):
        if obj is None:
            return
        if obj.isInstance() or obj.isCut():
            name = getattr(obj, "cell", "")
            if name:
                refs.add(name)
                if libs is not None:
                    lib = getattr(obj, "libpath", "") or ""
                    if lib and name not in libs:
                        libs[name] = lib
        for child in getattr(obj, "children", []):
            self._collectInstanceCells(child, refs, libs)

    def _missingInstanceCellLibraries(self):
        """{cell name: libpath} for the cells still not loaded."""
        refs, libs = set(), {}
        for cell in self.cells.values():
            self._collectInstanceCells(cell, refs, libs)
        missing = refs - set(self.cells.keys())
        return {n: libs[n] for n in missing if n in libs}

    def loadMissingFromLibraries(self, cicfile):
        """Load referenced cells from the LIBRARY they name.

        `fromJsonFilesWithDependencies` resolves a missing cell from a
        sibling .cic, which covers a design's own subcells and nothing
        else: a device comes from a library that is a different repo,
        reached through a symlink, and the .cic that holds it is not a
        sibling of anything.

        The instance says where to look. `libpath` names the library
        directory -- design/REY_ATR_SKY130A, usually a symlink into the
        library's own repo -- and the library .cic sits BESIDE that
        directory, named after it: design/REY_ATR_SKY130A.cic, 210
        cells. Resolve the symlink and it is one join away.

        This matters because a .cic records a device instance as four
        Port rects and a reference; the cell's own metal is in the
        library. Without it a checker sees ~4 rects where the cell has
        ~40, and anything a route collides with that is not one of
        those four is invisible. Measured: LELOTEMP_CMPR's n_mirr_load
        reported "0 shorts" while the extracted netlist had three nets
        merged into VSS, and the same blindness invented opens -- a
        supply came back "split into 8 components" because the metal
        joining those pieces lives inside the cells.

        Nothing is passed on the command line, so the blind
        configuration cannot be reached by forgetting a flag.
        """
        root = os.path.dirname(os.path.abspath(cicfile))
        tried = set()
        loaded = 0
        while True:
            libs = self._missingInstanceCellLibraries()
            if not libs:
                break
            progress = False
            for name, libpath in sorted(libs.items()):
                for cand in self._libraryCandidates(root, libpath, name):
                    if cand in tried or not os.path.exists(cand):
                        continue
                    tried.add(cand)
                    try:
                        self.fromJsonFiles(cand)
                        loaded += 1
                        progress = True
                    except Exception as e:
                        logging.getLogger("Design").warning(
                            f"{name}: could not read {cand}: {e}")
                    break
            if not progress:
                break
        return loaded

    def _libraryCandidates(self, root, libpath, name):
        """Where a library cell's .cic might be, most likely first."""
        out = []
        for base in (os.path.join(root, libpath),
                     os.path.join(root, "..", libpath)):
            libdir = os.path.realpath(base)
            if not os.path.isdir(libdir):
                continue
            parent = os.path.dirname(libdir)
            stem = os.path.basename(libdir)
            #- the library .cic BESIDE the library directory, named
            #- after it -- design/REY_ATR_SKY130A.cic for the cells in
            #- design/REY_ATR_SKY130A/
            out.append(os.path.join(parent, stem + ".cic"))
            out.append(os.path.join(parent, stem + ".cic.gz"))
            #- ...or one file per cell inside it
            out.append(os.path.join(libdir, name + ".cic"))
            out.append(os.path.join(libdir, name + ".cic.gz"))
        return out

    def toJson(self):
        obj = dict()
        obj["cells"] = list()
        for cname in self.cellNames():
            c = self.cells[cname]
            obj["cells"].append(c.toJson())

        return obj

    def add(self,c):

        if(c is None):
            return

        if(c.name not in self.cells):
            self.cells[c.name] = c
            self.cellnames.append(c.name)

    def define(self, cell, before=None):
        """Put a cell in the design, DEFINED BEFORE IT IS USED.

        `add` appends, which is right for cells arriving from a file.
        A cell BUILT during a run is different: something is about to
        instantiate it, and every reader -- the .cic writer, the magic
        printer, `getLayoutCell` -- must find it already defined. So
        it goes to the front, replacing any name it takes over.

        This is design bookkeeping and it lives here, with `cells` and
        `cellnames` and the ordering rule in `cellNames`, rather than
        in whatever recipe happened to build the thing.
        """
        if cell is None:
            return None
        name = cell.name
        self.cells[name] = cell
        if name in self.cellnames:
            self.cellnames.remove(name)
        if before and before in self.cellnames:
            self.cellnames.insert(self.cellnames.index(before), name)
        else:
            self.cellnames.insert(0, name)
        return cell

    def buildSubcells(self, parent, specs, build):
        """Split `parent`'s netlist and build a cell per part.

        THE HIERARCHY IS A PROPERTY OF THE NETLIST: membership and
        boundary nets follow from which instances a part claims (see
        core/hierarchy.py), so each part can be built as a cell in its
        own right, in memory, in one pass -- which is what the old
        two-pass build with a generated <CELL>_HIER.spice bought.

        Splitting a netlist into cells and defining them IS design
        construction, so it happens here. What a part becomes is not:
        `build(entry, subckt)` is the caller's, and returns the built
        cell. Returns the plan, one entry per part.
        """
        from .hierarchy import plan_from_netlist, split_subckt
        wanted = [s for s in specs if s.get("match")]
        if not wanted:
            return []
        plan = plan_from_netlist(parent.ckt, wanted, parent.name)
        if not plan:
            return []
        made = split_subckt(parent.ckt, plan)
        for entry in plan:
            cell = build(entry, made[entry["stack"]])
            self.define(cell, before=parent.name)
        return plan

    def cellNames(self):
        """Every cell, LOWER LEVELS FIRST.

        A design is a hierarchy, so a cell can only be understood after
        the cells it holds -- and every consumer that writes a
        definition before its uses depends on that: the .cic this
        design writes back, the SVG whose <use> can only name a group
        already emitted, a GUI listing the tree.

        Load order does not give it. Cells arrive one file at a time
        and merge by name, so two files decide the order between them
        by which was named first: LELOTEMP_CCMP.cic sorts ahead of
        LELOTEMP_CMP.cic and put a cell before its own contents. The
        dependency loop below is worse than alphabetical -- it loads a
        MISSING cell after everything that referenced it, by
        construction.

        This is where cuts have always been inserted at the front
        "like C++", one symptom patched at its own source. Sort the
        whole list instead, in place, so a caller holding an index into
        `cellnames` still agrees with it.
        """
        order, done, active = [], set(), set()

        def visit(name):
            if name in done or name in active or name not in self.cells:
                return
            active.add(name)
            refs = set()
            self._collectInstanceCells(self.cells[name], refs)
            for r in sorted(refs):
                visit(r)
            active.discard(name)
            done.add(name)
            order.append(name)

        for name in list(self.cellnames):
            visit(name)
        #- a name with no cell behind it is not ours to drop
        order += [n for n in self.cellnames if n not in done]
        self.cellnames[:] = order
        return self.cellnames


    def getCell(self,name):
        return self.cells[name]

    def registerPrimitiveProvider(self, provider):
        if provider is None:
            return
        self.primitiveProviders.append(provider)

    def generatePrimitiveLayout(self, subckt_name, instance):
        for provider in self.primitiveProviders:
            if not provider.supports(self, subckt_name):
                continue
            cell = provider.generate(self, subckt_name, instance)
            if cell is not None:
                return cell
        return None

    def getPrimitivePortOrder(self, subckt_name):
        for provider in self.primitiveProviders:
            ports = provider.canonical_port_order(subckt_name)
            if ports:
                return ports
        return []


    def read(self,filename):
        import cicspi as spi
        #Read JSON
        buffer = ""
        with open(filename)as fi:

            for line in fi:
                if(re.search(r"^\s*//",line)):
                    continue
                buffer += line

            obj = json.loads(buffer)

        #Read Spice

        spifile = filename.replace(".json",".spi")
        if(os.path.exists(spifile)):
            sp = spi.SpiceParser()
            sp.parseFile(spifile)

        if("cells" in obj):
            for c in obj["cells"]:
                if("name" not in c):
                    continue
                c = Cell()
                c.obj = c
