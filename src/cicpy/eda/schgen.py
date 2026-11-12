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
symbol body (``sides`` turns one another way). ``pin`` returns a pin's
absolute position for drawing wires, and ``wlab`` draws a wire with a
label at its middle, split there, because xschem only joins a label to
a wire END. ``write`` draws a frame round the sheet, see ``frame``.

Instances are placed unrotated; that is enough for generated sheets and
keeps the pin arithmetic exact.
"""
import logging
import os
import re

log = logging.getLogger("schgen")

#- lab_pin rotations, named by where the TEXT goes from the connection
#- point: rot 0 has the point on its right, so a pin on the LEFT of a
#- body takes LEFT. xschem turns clockwise with y down, so rot 1 stands
#- the text up from the point and rot 3 hangs it below: a pin on top of
#- a body takes UP, or its label is written across the body
LEFT, UP, RIGHT, DOWN = 0, 1, 2, 3

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
        self.box = (min(xs), min(ys), max(xs), max(ys))
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
        self.L += port_row(self.pins)

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
        """A label; rot is where the text goes from the point: LEFT,
        RIGHT, UP or DOWN."""
        self.L.append(f"C {{devices/lab_pin.sym}} {_n(x)} {_n(y)} {rot} 0 "
                      f"{{name=l{self.nid()} sig_type=std_logic lab={net}}}")

    def wlab(self, x1, y1, x2, y2, rot, net):
        """A wire with a label at its middle, split there so the label
        lands on a wire end."""
        xm, ym = (x1 + x2)//2, (y1 + y2)//2
        self.wire(x1, y1, xm, ym)
        self.wire(xm, ym, x2, y2)
        self.lab(xm, ym, rot, net)

    def inst(self, ref, name, x, y, props="", sides=None, **conn):
        """Place symbol ref unrotated at (x, y) and label the pins in
        conn (pin=net). Pin names that are not Python identifiers go in
        as a dict: inst(..., **{"in": "A"}).

        sides  {pin: LEFT | RIGHT | UP | DOWN} where a label should not
               point away from the body: a supply pin on top of a gate
               reads better with its net beside it (RIGHT) than stood
               on end above it, and a column of gates packs closer."""
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
            if sides and p in sides:
                side = sides[p]
            self.lab(x + px, y + py, side, net)
        return sym

    # -- output ------------------------------------------------------
    def write(self, outdir, symbol=True):
        """Write <cell>.sch, and unless symbol=False a box <cell>.sym."""
        boxes = [(x + s.box[0], y + s.box[1], x + s.box[2], y + s.box[3])
                 for s, x, y in getattr(self, "_placed", {}).values()]
        with open(os.path.join(outdir, self.cell + ".sch"), "w") as f:
            f.write("\n".join(frame(self.L, boxes=boxes)) + "\n")
        if symbol:
            write_box_symbol(os.path.join(outdir, self.cell + ".sym"),
                             self.pins)
        log.info(f"wrote {self.cell}")


#- xschem's text, measured on its SVG: a character of size 1 is about
#- 25 wide in the proportional font and a line 50 high. A label is 0.33
_CW, _CH, _LAB = 25, 50, 0.33
_C = re.compile(r"^C\s+\{([^}]*)\}\s+(\S+)\s+(\S+)\s+(\d)\s+\d\s+\{(.*)")
_T = re.compile(r"^T\s+\{(.*)\}\s+(\S+)\s+(\S+)\s+\d\s+\d\s+(\S+)")
_N = re.compile(r"^N\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")


def _labw(name):
    """The room a label or port takes from its point, text and arrow."""
    return 20 + _CW*_LAB*len(name)


def port_row(pins, x=-1400, y=-740, pitch=160):
    """The ipin/opin lines of a sheet's ports, in order, left to right.
    They sit a pitch apart, further where two names would meet: an
    input has its name on the left of its arrow, an output on the
    right, so a long output followed by an input needs both widths."""
    L = []
    room = None
    for i, (p, d) in enumerate(pins):
        left, right = (_labw(p), 20) if d == "in" else (20, _labw(p))
        if room is not None:
            x += max(pitch, 10*round((room + left + 30)/10))
        room = right
        sym = {"in": "ipin", "out": "opin"}.get(d, "iopin")
        L.append(f"C {{devices/{sym}.sym}} {_n(x)} {y} "
                 f"0 0 {{name=p{i} lab={p}}}")
    return L


def frame(lines, margin=40, boxes=None):
    """The lines of a schematic with a frame drawn round all of it.

    xschem leaves text out of the area it fits to the page when it
    plots without a display (``xschem -x --svg``, which is how the
    documentation is made): a title, a note that runs past the last
    device and the names of the ports at the edge are cut off. A frame
    is a drawn object, so the plot keeps everything inside it. The
    extent of text and labels is estimated from their length.

    boxes  [(x1, y1, x2, y2)] of the placed symbols, when known (Sheet
           knows); without it every instance counts as 150 each way."""
    xs, ys = [], []

    def see(x1, y1, x2, y2):
        xs.extend((x1, x2))
        ys.extend((y1, y2))

    for l in lines:
        m = _T.match(l)
        if m:
            x, y, size = float(m.group(2)), float(m.group(3)), float(m.group(4))
            see(x, y, x + _CW*size*len(m.group(1)), y + _CH*size)
            continue
        m = _N.match(l)
        if m:
            see(*map(float, m.groups()))
            continue
        m = _C.match(l)
        if not m:
            continue
        ref, x, y, rot = m.group(1), float(m.group(2)), float(m.group(3)), int(m.group(4))
        lab = re.search(r"lab=([^\s}]+)", m.group(5))
        kind = os.path.basename(ref)
        if kind in ("lab_pin.sym", "ipin.sym", "opin.sym", "iopin.sym") and lab:
            w = _labw(lab.group(1))
            if kind in ("opin.sym", "iopin.sym"):
                rot = RIGHT
            dx, dy = {LEFT: (-w, 0), RIGHT: (w, 0),
                      UP: (0, -w), DOWN: (0, w)}[rot]
            see(x - 15, y - 15, x + 15, y + 15)
            see(x, y, x + dx, y + dy)
        elif boxes is None:
            see(x - 150, y - 150, x + 150, y + 150)
    for b in boxes or ():
        see(*b)
    if not xs:
        return list(lines)
    x1, y1 = _n(10*((min(xs) - margin)//10)), _n(10*((min(ys) - margin)//10))
    x2, y2 = _n(10*(-((-max(xs) - margin)//10))), _n(10*(-((-max(ys) - margin)//10)))
    return list(lines) + [
        f"P 4 5 {x1} {y1} {x2} {y1} {x2} {y2} {x1} {y2} {x1} {y1} {{dash=4}}"]


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
    h, left, right = _box(pins)
    s.box = (-150, -h - 22, 150, h)
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
         #- the instance name over the box's corner: beside the box
         #- it lands on the label of the third output
         f"T {{@name}} -130 {-h - 22} 0 0 0.25 0.25 {{}}",
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
