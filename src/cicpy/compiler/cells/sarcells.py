#!/usr/bin/env python3
"""The hand-written SAR cells: cIcCells::CapCell, CDAC and SAR.

These are the three cells in ciccreator that are CODE rather than
pattern: the ESSCIRC'16 capacitor bank, the C-DAC column built from
it, and the SAR top that arranges switches, DACs and logic and draws
the bus between them. Ports of cic-core/src/cells/{capcell,cdac,sar}.cpp.

Transcribed deliberately close to the C++ -- same names, same
arithmetic, same order -- because every constant in here (the `5`
rows, the contact index tables) is layout, and a paraphrase is a
different chip.
"""
import logging

from ...core.cut import Cut
from ...core.port import Port
from ...core.rect import Rect, sortLeftOnTop
from ...core.rules import Rules
from ..registry import cicclass
from .layoutcells import LayoutCell

log = logging.getLogger("cicpy.compiler")


@cicclass("cIcCells::CapCell")
class CapCell(LayoutCell):
    """The 32-finger MOM capacitor bank with its binary tap ladder."""

    def __init__(self, name=""):
        super().__init__(name)
        self.usem3_ = False
        self.usem5_ = False
        self.heightIncreaseMult_ = 1
        self.msw = 0
        self.xorg = 0
        self.yMax = 0

    def usem3(self, v):
        self.usem3_ = bool(int(v))

    def usem5(self, v):
        self.usem5_ = bool(int(v))

    def heightIncreaseMult(self, v):
        self.heightIncreaseMult_ = int(v)

    def maxcap(self, v):
        #- accepted for compatibility; the C++ has the property and
        #- reads it nowhere
        self._maxcap = int(v)

    def calcBoundingRect(self):
        r = super().calcBoundingRect()
        mw = Rules.getInstance().get("M2", "width")
        r.adjust(0, mw // 2, 0, -mw // 2)
        return r

    def getAvssConnectRect(self, rect):
        """The stub that joins this cap's AVSS to the shared rail."""
        from ...core.cell import Cell
        cell = Cell()
        c = Cut("M1", "M2", 1, 2)
        y = c.height() / 2.0
        c.moveTo(0, -y)
        r = Rect("M2", 0, -rect.height() / 2.0, self.ports["AVSS"].x1, c.width())
        cell.add(c)
        cell.add(r)
        cell.updateBoundingRect()
        cell.moveTo(0, rect.centerY() - y)
        return cell

    def place(self):
        self.noPowerRoute = True
        self.setBoundaryIgnoreRouting(False)

        super().place()

        rules = Rules.getInstance()
        ms = rules.get("M4", "capspace")
        ct = Cut.getInstance("M1", "M4", 2, 1)
        mw = ct.height()

        y = 0
        count = 32
        self.msw = msw = ms + mw
        mswy = ms + mw + ct.width() // 2 - mw // 2
        msc = ct.width() // 2 + ms * 2 * self.heightIncreaseMult_
        b = 5

        height = mswy * 2 + msc * b + mw
        xm1 = 0
        self.xorg = xorg = ct.width() + ms * 2
        x = xorg
        first = True

        rects = []
        if self.usem5_:
            rects.append(Rect("M5", x - msw, y, mw, height))
        for _ in range(count):
            r = Rect("M4", x, y, mw, height)
            rects.append(r)
            if first:
                p = Port("CTOP")
                p.set(r)
                self.add(p)
                first = False
            rects.append(Rect("M2", x, y, mw, height - mw))
            rects.append(Rect("M4", x + msw, y + msw, mw, height - msw * 2))
            if self.usem3_:
                rects.append(Rect("M3", x + msw, y + msw, mw, height - msw * 2))
            if self.usem5_:
                rects.append(Rect("M5", x + msw, y, mw, height))
            x = x + msw * 2

        if self.usem5_:
            ctdum = Cut.getInstance("M2", "M5", 1, 2)
        else:
            ctdum = Cut.getInstance("M2", "M4", 1, 2)
        ctdum.moveTo(x + msw, y + height // 2 - ctdum.height())
        self.add(ctdum)

        for _ in range(count):
            rects.append(Rect("M2", x + msw, y, mw, height))
            rects.append(Rect("M3", x + msw, y, mw, height))
            rects.append(Rect("M4", x + msw, y, mw, height))
            if self.usem5_:
                rects.append(Rect("M5", x + msw, y, mw, height))

        rects.append(Rect("M4", x, y, mw, height))
        rects.append(Rect("M2", x, y, mw, height))

        y1a = mswy
        y1b = y1a + msc * b
        y2 = y1a + msc * (b - 3)
        y4 = y1a + msc * (b - 1)
        y8 = y1a + msc * (b - 2)
        y16 = y1a + msc * (b - 4)
        self.yMax = height

        if self.usem5_:
            rects.append(Rect("M5", xorg - msw, y, x - xorg + msw * 2, mw))
            rects.append(Rect("M5", xorg - msw, height - mw, x - xorg + msw * 2, mw))

        vss1 = Rect("M2", xorg, y, x - xorg + msw, mw)
        ctop1 = Rect("M4", xorg, y, x - xorg, mw)
        ctop2 = Rect("M4", xorg, height - mw, x - xorg, mw)
        vss2 = Rect("M2", xorg, height - mw, x - xorg + msw, mw)
        p = Port("AVSS")
        p.set(vss1)
        self.add(p)

        taps = []
        for name, yy in (("C1A", y1a), ("C1B", y1b), ("C2", y2),
                         ("C4", y4), ("C8", y8), ("C16", y16)):
            bar = Rect("M1", xm1, yy, x - xm1, mw)
            pad = Rect("M1", xm1, yy, ct.width(), mw)
            p = Port(name)
            p.set(pad)
            self.add(p)
            taps.append(bar)
        c1a, c1b, c2, c4, c8, c16 = taps

        rects += [c16, c1a, c1b, c2, c4, c8, vss1, vss2, ctop1, ctop2]

        #- which fingers each binary weight contacts; the tables ARE
        #- the capacitor ratios
        self.addContacts("XRES1A", "C1A", y1a, [15], c1a)
        self.addContacts("XRES1B", "C1B", y1b, [49], c1b)
        self.addContacts("XRES2", "C2", y2, [17, 47], c2)
        self.addContacts("XRES4", "C4", y4, [13, 19, 45, 51], c4)
        self.addContacts("XRES8", "C8", y8, [9, 11, 21, 23, 41, 43, 53, 55], c8)
        self.addContacts("XRES16", "C16", y16,
                         [1, 3, 5, 7, 25, 27, 29, 31, 33, 35, 37, 39,
                          57, 59, 61, 63], c16)
        for r in rects:
            self.add(r)

    def addContacts(self, name, _port, y, array, cp):
        ms = Rules.getInstance().get("M2", "space")
        ctres = Cut.getInstance("M1", "M4", 2, 1)
        inst = self.getInstanceFromInstanceName(name)
        if inst is None:
            return
        inst.moveTo(ctres.width(), y)
        cp.setLeft(inst.x2)

        for x in array:
            ct = Cut.getInstance("M1", "M4", 1, 2)
            mw = ct.width()
            ct.moveTo(self.xorg + self.msw * x, y + mw // 2 - ct.height() // 2)
            ra = Rect("M2", ct.x1, 0, ct.width(), ct.y1 - ms)
            rb = Rect("M2", ct.x1, ct.y2 + ms, ct.width(),
                      self.yMax - ct.y2 - ms)
            self.add(ct)
            if ra.height() - mw > mw:
                self.add(ra)
            if rb.height() - mw > mw:
                self.add(rb)


@cicclass("cIcCells::CDAC")
class CDAC(LayoutCell):
    """A column of CapCells, one per bit, ringed by the CP<> nets."""

    def __init__(self, name=""):
        super().__init__(name)
        self.firstinst = None
        self.inst = None

    def place(self):
        self.noPowerRoute = True
        self.setBoundaryIgnoreRouting(False)

        rules = Rules.getInstance()
        xs = rules.get("M1", "space")
        xw = rules.get("M1", "width")

        nodes = self.subckt.nodes if self.subckt is not None else []
        i = sum(1 for s in nodes if "CP" in s) - 1

        x = (xw + xs * 2) * (i + 2)
        y = 0
        first = True
        for ckt_inst in (self.subckt.instances if self.subckt is not None else []):
            self.inst = self.addInstance(ckt_inst, x, y)
            y += self.inst.height()
            if first:
                self.firstinst = self.inst
                first = False

        self.adjust(-xs * 2 + xw, 0, 0, 0)

        for k in range(i, -1, -1):
            self.addRouteRing("M2", "CP<%d>" % k, "l", 1, 2, False)

        for graph in self.getNodeGraphs("AVSS"):
            for p in graph.ports:
                if not p.isInstancePort():
                    continue
                if "C" not in (getattr(p, "childName", "") or ""):
                    continue
                r = p.parent
                if r is None or not r.isInstance():
                    continue
                cell = getattr(r, "layoutcell", None) or getattr(r, "_cell_obj", None)
                if isinstance(cell, CapCell):
                    rect = cell.getAvssConnectRect(p)
                    rect.translate(r.x1, 0)
                    self.add(rect)

        self.updateBoundingRect()

    def route(self):
        self.addRouteConnection("CP", "", "M3", "left", "")

        if self.firstinst is not None:
            rects1 = self.firstinst.findRectanglesByNode("AVSS", "")
            if rects1:
                self.addPort("AVSS", rects1[0])
        if self.inst is not None:
            rects2 = self.inst.findRectanglesByNode("CTOP", "")
            if rects2:
                self.addPort("CTOP", rects2[0])

        super().route()
        self.trimRouteRing("CP<", "left", "b")
        self.updateBoundingRect()


@cicclass("cIcCells::SAR")
class SAR(LayoutCell):
    """The SAR top: switches, two DAC columns, logic, and the bus."""

    def __init__(self, name=""):
        super().__init__(name)
        self.usem5_ = False
        self.sarn = None
        self.sarp = None

    def usem5(self, v):
        self.usem5_ = bool(int(v))

    def getCellWidth(self, groups, group):
        if group not in groups:
            return 0
        ckt = groups[group][0]
        cell = self.design.cells.get(ckt.subcktName) if self.design else None
        return cell.width() if cell is not None else 0

    def placeAlternateMirror(self, groups, group, i, x, y, xoffset):
        inst = None
        ind = i
        xc = x
        for ckt in groups.get(group, []):
            inst = self.addInstance(ckt, xc, y)
            if ind % 2 != 0:
                inst.setAngle("MY")
            ind += 1
            xc += inst.width() + xoffset
        return inst

    def place(self):
        self.noPowerRoute = True
        self.setBoundaryIgnoreRouting(False)

        groups = {}
        if self.subckt is not None:
            for ckt_inst in self.subckt.instances:
                if ckt_inst is not None:
                    groups.setdefault(ckt_inst.groupName, []).append(ckt_inst)

        rules = Rules.getInstance()
        ms = rules.get("M3", "space")
        mw = rules.get("M3", "width")
        cut = Cut.getInstance("M1", "M2", 2, 1)
        msw = ms + mw + (cut.width() - mw) // 2

        cdacwidth = self.getCellWidth(groups, "XDAC")
        switchwidth = self.getCellWidth(groups, "XB")

        centerx = (cdacwidth * 2 + ms * 5 + mw * 4) // 2
        x = centerx - switchwidth
        y = 0

        inst = self.placeAlternateMirror(groups, "XB", 1, x, y, 0)
        if inst is not None:
            y += inst.height() + msw

        inst = self.placeAlternateMirror(groups, "XDAC", 1, 0, y, ms * 5 + mw * 2)
        if inst is not None:
            y = inst.y2

        graphs = self.getNodeGraphs("CN<|D<|CP<")
        yc = y + msw * 2
        y += msw * len(graphs) + msw * 10 - mw

        ctrwidth = self.getCellWidth(groups, "XA")
        all_ctrwidth = ctrwidth * len(groups.get("XA", []))
        x = centerx - all_ctrwidth // 2

        inst = self.placeAlternateMirror(groups, "XA", 0, x, y, 0)
        maxy = inst.y2 if inst is not None else y

        y = maxy + msw * 4
        self.updateBoundingRect()

        yc = self.addSarRouting(yc, msw, mw)

        def sortkey(graph):
            #- the bus orders by where each net enters the logic row
            rect_a = graph.getRectangles("", "SARDIG", "")
            if not rect_a:
                return 0
            sortLeftOnTop(rect_a)
            return rect_a[0].y2

        graphs = sorted(graphs, key=sortkey)

        for graph in graphs:
            r0 = Rect("M3", self.x1, yc, self.width(), mw)
            yc += msw
            xfmin, xfmax = float("inf"), float("-inf")

            for r in graph.getRectangles("", "SARDIG", ""):
                r1 = Rect("M4", r.x1, r0.y2, mw, r.y1 - r0.y2)
                c = Cut.getInstance("M3", "M4", 1, 2)
                c.moveCenter(r1.centerX(), r0.centerY())
                self.add(c)
                self.add(r1)
                self.addPort(graph.name, r1)
                xfmin = min(xfmin, r1.x1)
                xfmax = max(xfmax, r1.x2)

            for r in graph.getRectangles("", "CDAC", ""):
                c = Cut.getInstance("M2", "M3", 1, 2)
                c.moveCenter(r.centerX(), r0.centerY())
                r1 = Rect("M2", r.x1, r.y2, mw, r0.y1 - r.y2)
                self.add(c)
                self.add(r1)
                xfmin = min(xfmin, r1.x1)
                xfmax = max(xfmax, r1.x2)

            r0.setLeft(xfmin)
            r0.setRight(xfmax)
            self.add(r0)

        self.updateBoundingRect()

    def addSarRouting(self, y, msw, mw):
        rules = Rules.getInstance()
        ms = rules.get("M3", "space")

        y += msw - mw
        self.sarn = Rect("M4", self.x1 + msw, y, self.width() - 2 * msw, mw)
        self.add(self.sarn)
        y += 2 * msw
        self.sarp = Rect("M4", self.x1 + msw, y, self.width() - 2 * msw, mw)
        self.add(self.sarp)
        y += msw
        sarn, sarp = self.sarn, self.sarp

        if "SARP" in self.ports:
            self.ports["SARP"].set(sarp)
            self.ports["SARN"].set(sarn)

        sarn_cdac = self.findRectanglesByNode("SARN", "", "CDAC")
        if sarn_cdac:
            r_sarn = sarn_cdac[0]
            ra = Rect("M3", r_sarn.x1, r_sarn.y2, mw, sarn.y1 - r_sarn.y2)
            ct = Cut.getInstance("M3", "M4", 1, 2)
            ct.moveTo(ra.x1, ra.y1)
            ct1 = Cut.getInstance("M3", "M4", 2, 1)
            ct1.moveTo(r_sarn.x1, sarn.y1)
            ra.setTop(ct1.y2)
            self.add(ra)
            self.add(ct)
            self.add(ct1)

        sarp_cdac = self.findRectanglesByNode("SARP", "", "CDAC")
        if sarp_cdac:
            r_sarp = sarp_cdac[0]
            ra = Rect("M3", r_sarp.x1, r_sarp.y2, mw, sarp.y1 - r_sarp.y2)
            ct = Cut.getInstance("M3", "M4", 1, 2)
            ct.moveTo(ra.x1, ra.y1)
            ct1 = Cut.getInstance("M3", "M4", 2, 1)
            ct1.moveTo(r_sarp.x1, sarp.y1)
            ra.setTop(ct1.y2)
            ctx1 = ct.x1
            self.add(ra)
            self.add(ct)
            self.add(ct1)
            sarp.setLeft(ctx1)
            sarn.setLeft(ctx1)

        sarp_cmp = self.findRectanglesByNode("SARP", "", "SARCMP")
        if sarp_cmp and sarp_cmp[0] is not None:
            r = sarp_cmp[0]
            ct_cmp = Cut.getInstance("M2", "M4", 2, 1)
            if self.usem5_:
                ct2 = Cut.getInstance("M4", "M5", 2, 1)
                ct1 = Cut.getInstance("M4", "M5", 1, 2)
            else:
                ct2 = Cut.getInstance("M4", "M3", 2, 1)
                ct1 = Cut.getInstance("M4", "M3", 1, 2)
            ycc = sarp.y2 + ct2.height() * 4
            ra = Rect("M4", r.x1, ycc, mw, r.y1 - ycc)
            ct_cmp.moveTo(r.x1, r.y1)
            layer5 = "M5" if self.usem5_ else "M3"
            rb = Rect(layer5, ra.x1, sarp.y1, mw, ycc - sarp.y1)
            ct2.moveTo(ra.x1, sarp.y1)
            ct1.moveTo(ra.x1, ra.y1)
            for rr in (ct_cmp, rb, ra, ct2, ct1):
                self.add(rr)

        sarn_cmp = self.findRectanglesByNode("SARN", "", "SARCMP")
        if sarn_cmp and sarn_cmp[0] is not None:
            r = sarn_cmp[0]
            ct_cmp = Cut.getInstance("M2", "M3", 2, 1)
            cta_cmp = Cut.getInstance("M3", "M4", 2, 1)
            if self.usem5_:
                ct2 = Cut.getInstance("M4", "M5", 2, 1)
                ct1 = Cut.getInstance("M4", "M5", 1, 2)
            else:
                ct2 = Cut.getInstance("M4", "M3", 2, 1)
                ct1 = Cut.getInstance("M4", "M3", 1, 2)
            ycc = sarp.y2 + ct2.height() * 4
            ra = Rect("M4", r.x2 + ms, ycc, mw, r.y1 - ycc)
            cta_cmp.moveTo(r.x2 + ms + mw - ct_cmp.width(), r.y1)
            ct_cmp.moveTo(r.x1, r.y1)
            layer5 = "M5" if self.usem5_ else "M3"
            rb = Rect(layer5, ra.x1, sarn.y1, mw, ycc - sarn.y1)
            ct2.moveTo(ra.x1, sarn.y1)
            ct1.moveTo(ra.x1, ra.y1)
            for rr in (cta_cmp, ct_cmp, rb, ra, ct2, ct1):
                self.add(rr)

        y += msw
        return y
