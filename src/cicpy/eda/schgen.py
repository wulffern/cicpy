"""Write xschem schematics from Python, readable by a human.

A generator script draws a schematic the way a person would: repeated
devices as BUS instances (``xmp[6:0]`` is seven PMOS, its pins take comma
net lists), wires for local nets, and labels only for supplies and the
nets that leave a block. The pin positions come from the symbols
themselves, so a generator never hard codes a pin offset::

    from cicpy.eda.schgen import Sheet, bus, nets

    sh = Sheet("MY_CELL", [("VDD", "in"), ("VSS", "in"), ("Y", "out")],
               search=["../design"], title="MY_CELL: an inverter")
    sh.inst("MY_LIB/PCH.sym", "xp", 0, 0, G="A", S="VDD", D="Y", B="VDD")
    sh.inst("MY_LIB/NCH.sym", "xn", 0, 150, G="A", D="Y", S="VSS")
    sh.write("../design/MY_LIB")      # MY_CELL.sch and a box MY_CELL.sym

``inst`` puts a label on each pin it is given, pointing away from the
symbol body. ``pin`` returns a pin's absolute position for drawing wires,
and ``wlab`` draws a wire with a label at its middle, split there,
because xschem only joins a label to a wire END.

Instances are placed unrotated; that is enough for generated sheets and
keeps the pin arithmetic exact.
"""
import logging
import os
import re

log = logging.getLogger("schgen")

#- lab_pin rotations: the label's connection point is on its right for
#- rot 0, so a pin on the LEFT of a body takes rot 0
LEFT, DOWN, RIGHT, UP = 0, 1, 2, 3

_PIN = re.compile(r"^B\s+5\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\{(.*)")
_LINE = re.compile(r"^L\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
_RECT = re.compile(r"^B\s+[0-46-9]\d*\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
_POLY = re.compile(r"^P\s+\d+\s+\d+\s+([-0-9.\s]+)\{")


def bus(name, w):
    """The xschem bus instance name for w copies: xdf[9:0]."""
    return f"{name}[{w-1}:0]" if w > 1 else name


def nets(prefix, idx):
    """A comma net list for a bus pin, in the instance's index order:
    nets("N", range(6, -1, -1)) is N6,N5,...,N0 for x[6:0]."""
    return ",".join(f"{prefix}{i}" for i in idx)


class Symbol:
    """The pins of an xschem symbol: name -> (x, y, side), side being the
    lab_pin rotation that points away from the body."""

    def __init__(self, path):
        self.path = path
        self.pins = {}
        self.order = []
        body = []
        pins = []
        with open(path) as f:
            for line in f:
                m = _PIN.match(line)
                if m:
                    x1, y1, x2, y2 = map(float, m.groups()[:4])
                    nm = re.search(r"name=([^\s}]+)", m.group(5))
                    if nm:
                        pins.append((nm.group(1), (x1 + x2)/2, (y1 + y2)/2))
                    continue
                for rx in (_LINE, _RECT):
                    m = rx.match(line)
                    if m:
                        x1, y1, x2, y2 = map(float, m.groups())
                        body += [(x1, y1), (x2, y2)]
                        break
                else:
                    m = _POLY.match(line)
                    if m:
                        v = list(map(float, m.group(1).split()))
                        body += list(zip(v[0::2], v[1::2]))
        pts = body or [(x, y) for _, x, y in pins]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs))/2, (min(ys) + max(ys))/2
        hx = max((max(xs) - min(xs))/2, 1e-9)
        hy = max((max(ys) - min(ys))/2, 1e-9)
        for n, x, y in pins:
            dx, dy = (x - cx)/hx, (y - cy)/hy
            #- ties go to top/bottom: a MOS source or drain sits on a
            #- corner of the drawing and reads best labelled up or down
            if abs(dy) >= abs(dx):
                side = UP if dy < 0 else DOWN
            else:
                side = LEFT if dx < 0 else RIGHT
            self.pins[n] = (x, y, side)
            self.order.append(n)


class Sheet:
    """One generated schematic and its box symbol.

    cell    the cell name, written as <cell>.sch and <cell>.sym
    pins    [(name, "in" | "out" | "inout")], the order of the ports
    search  directories that symbol references ("LIB/CELL.sym") are
            relative to, as in xschem's XSCHEM_LIBRARY_PATH
    title   a line of text at the top of the sheet
    """

    def __init__(self, cell, pins, search=(), title=None):
        self.cell = cell
        self.pins = list(pins)
        self.search = list(search)
        self.L = ["v {xschem version=3.4.7 file_version=1.2}", "G {}",
                  "K {}", "V {}", "S {}", "E {}"]
        self._n = 0
        self._syms = {}
        self.local = {}
        if title:
            self.text(title, -1450, -820, 0.5)
        for i, (p, d) in enumerate(self.pins):
            sym = {"in": "ipin", "out": "opin"}.get(d, "iopin")
            self.L.append(f"C {{devices/{sym}.sym}} {-1400 + 160*i} -740 "
                          f"0 0 {{name=p{i} lab={p}}}")

    # -- symbols -----------------------------------------------------
    def symbol(self, ref):
        """The Symbol for a reference like REY_TR_SKY130A/REYTR_IVX1_CV.sym,
        found on the search path, or one of the sheets registered with
        add_local()."""
        if ref in self._syms:
            return self._syms[ref]
        if ref in self.local:
            s = self.local[ref]
        else:
            for d in self.search:
                p = os.path.join(d, ref)
                if os.path.exists(p):
                    s = Symbol(p)
                    break
            else:
                raise FileNotFoundError(
                    f"symbol {ref} not found in {self.search}")
        self._syms[ref] = s
        return s

    def add_local(self, ref, sheet):
        """Use another Sheet's box symbol for ref before it is written."""
        self.local[ref] = box_symbol(sheet.pins)

    def pin(self, name, pin):
        """The absolute position of an instance's pin."""
        sym, x, y = self._placed[name]
        px, py, _ = sym.pins[pin]
        return x + px, y + py

    # -- drawing -----------------------------------------------------
    def nid(self):
        self._n += 1
        return self._n

    def text(self, s, x, y, size=0.4):
        self.L.append(f"T {{{s}}} {x} {y} 0 0 {size} {size} {{}}")

    def wire(self, x1, y1, x2, y2):
        self.L.append(f"N {_n(x1)} {_n(y1)} {_n(x2)} {_n(y2)} {{}}")

    def path(self, *pts):
        """Wires through a list of points."""
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.wire(x1, y1, x2, y2)

    def lab(self, x, y, rot, net):
        """A label; rot LEFT (0) has its connection point on its right."""
        self.L.append(f"C {{devices/lab_pin.sym}} {_n(x)} {_n(y)} {rot} 0 "
                      f"{{name=l{self.nid()} sig_type=std_logic lab={net}}}")

    def wlab(self, x1, y1, x2, y2, rot, net):
        """A wire with a label at its middle, split there so the label
        lands on a wire end."""
        xm, ym = (x1 + x2)//2, (y1 + y2)//2
        self.wire(x1, y1, xm, ym)
        self.wire(xm, ym, x2, y2)
        self.lab(xm, ym, rot, net)

    def inst(self, ref, name, x, y, props="", **conn):
        """Place symbol ref unrotated at (x, y) and label the pins in
        conn (pin=net). Pin names that are not Python identifiers go in
        as a dict: inst(..., **{"in": "A"})."""
        sym = self.symbol(ref)
        if not hasattr(self, "_placed"):
            self._placed = {}
        self._placed[name] = (sym, x, y)
        extra = f" {props}" if props else ""
        self.L.append(f"C {{{ref}}} {_n(x)} {_n(y)} 0 0 "
                      f"{{name={name}{extra}}}")
        for p, net in conn.items():
            if net is None:
                continue
            if p not in sym.pins:
                raise KeyError(f"{ref} has no pin {p}, it has {sym.order}")
            px, py, side = sym.pins[p]
            self.lab(x + px, y + py, side, net)
        return sym

    # -- output ------------------------------------------------------
    def write(self, outdir, symbol=True):
        """Write <cell>.sch, and unless symbol=False a box <cell>.sym."""
        with open(os.path.join(outdir, self.cell + ".sch"), "w") as f:
            f.write("\n".join(self.L) + "\n")
        if symbol:
            write_box_symbol(os.path.join(outdir, self.cell + ".sym"),
                             self.pins)
        log.info(f"wrote {self.cell}")


def _n(v):
    """Coordinates as integers when they are."""
    return int(v) if float(v).is_integer() else v


def _box(pins):
    """Port positions of the box symbol: inputs left, outputs right."""
    ins = [p for p, d in pins if d != "out"]
    outs = [p for p, d in pins if d == "out"]
    h = 20*max(len(ins), len(outs), 1) + 10
    left = [(p, -150, -h + 20 + 20*i) for i, p in enumerate(ins)]
    right = [(p, 150, -h + 20 + 20*i) for i, p in enumerate(outs)]
    return h, left, right


def box_symbol(pins):
    """The Symbol that write_box_symbol would write, without a file."""
    s = Symbol.__new__(Symbol)
    s.path = None
    s.pins, s.order = {}, []
    _, left, right = _box(pins)
    for p, x, y in left:
        s.pins[p] = (x, y, LEFT)
        s.order.append(p)
    for p, x, y in right:
        s.pins[p] = (x, y, RIGHT)
        s.order.append(p)
    return s


def write_box_symbol(path, pins):
    """A subcircuit symbol: a box, inputs on the left, outputs on the
    right, 20 apart, in port order."""
    d = dict(pins)
    h, left, right = _box(pins)
    Y = ["v {xschem version=3.4.7 file_version=1.2}",
         'K {type=subcircuit\nformat="@name @pinlist @symname"\n'
         'template="name=x1"\n}',
         "T {@symname} -60 -6 0 0 0.3 0.3 {}",
         "T {@name} 135 -52 0 0 0.2 0.2 {}",
         f"P 4 5 130 {-h} -130 {-h} -130 {h} 130 {h} 130 {-h} {{}}"]
    for p, x, y in left:
        Y += [f"B 5 -152.5 {y-2.5} -147.5 {y+2.5} {{name={p} dir={d[p]}}}",
              f"L 4 -150 {y} -130 {y} {{}}",
              f"T {{{p}}} -125 {y-4} 0 0 0.2 0.2 {{}}"]
    for p, x, y in right:
        Y += [f"B 5 147.5 {y-2.5} 152.5 {y+2.5} {{name={p} dir=out}}",
              f"L 4 130 {y} 150 {y} {{}}",
              f"T {{{p}}} 125 {y-4} 0 1 0.2 0.2 {{}}"]
    with open(path, "w") as f:
        f.write("\n".join(Y) + "\n")
