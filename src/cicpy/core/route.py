
from .cell import Cell
from .rect import Rect, HorizontalRectangleFromTo, VerticalRectangleFromTo
from .text import Text
from .rules import Rules
import re

class Route(Cell):

    def __init__(self, net, layer, start, stop, options, routeType):
        super().__init__(net)
        self.routeLayer = layer
        self.routeType = "ROUTE_UNKNOWN"
        self.route = routeType
        self.options = options or ""
        self.net = net
        self.track = 0
        self.hasTrack = False
        self.startCuts = 0
        self.startVCuts = 0
        self.endCuts = 0
        self.endVCuts = 0
        self.cuts = 2
        self.vcuts = 1
        self.routeWidthRule = "width"
        self.fillvcut = False
        self.fillhcut = False
        self.antenna = False
        self.startRects = list(start or [])
        self.stopRects = list(stop or [])
        self.routes = list()
        self.addAfterRoute = list()
        self.leftAlignCut = True
        self.startOffset = "NO_OFFSET"
        self.stopOffset = "NO_OFFSET"
        self.startOffsetCut = "NO_OFFSET"
        self.endOffsetCut = "NO_OFFSET"
        self.startTrim = "NO_TRIM"
        self.endTrim = "NO_TRIM"
        self.startLayer = ""
        self.stopLayer = ""

        self.setBoundaryIgnoreRouting(False)

        if re.search(r"fillhcut", self.options):
            self.fillhcut = True
        if re.search(r"fillvcut", self.options):
            self.fillvcut = True
        if re.search(r"antenna", self.options):
            self.antenna = True

        if len(self.startRects) == 0 and len(self.stopRects) > 0:
            r = self.stopRects.pop(0)
            self.startRects.append(r)

        if re.search(r"trimstartleft(,|\\s+|$)", self.options):
            self.startTrim = "TRIM_START_LEFT"
        elif re.search(r"trimstartright(\\s+|,|$)", self.options):
            self.startTrim = "TRIM_START_RIGHT"

        if re.search(r"trimendleft(,|\\s+|$)", self.options):
            self.endTrim = "TRIM_END_LEFT"
        elif re.search(r"trimendright(\\s+|,|$)", self.options):
            self.endTrim = "TRIM_END_RIGHT"

        if re.search(r"offsethigh(,|\\s+|$)", self.options):
            self.startOffset = "HIGH"
        elif re.search(r"offsetlow(\\s+|,|$)", self.options):
            self.startOffset = "LOW"

        if re.search(r"startoffsetcuthigh(,|\\s+|$)", self.options):
            self.startOffsetCut = "HIGH"
        elif re.search(r"startoffsetcutlow(,|\\s+|$)", self.options):
            self.startOffsetCut = "LOW"

        if re.search(r"endoffsetcuthigh(,|\\s+|$)", self.options):
            self.endOffsetCut = "HIGH"
        elif re.search(r"endoffsetcutlow(,|\\s+|$)", self.options):
            self.endOffsetCut = "LOW"

        if re.search(r"offsethighend", self.options):
            self.stopOffset = "HIGH"
        elif re.search(r"offsetlowend", self.options):
            self.stopOffset = "LOW"

        m = re.search(r"track(\\d+)", self.options)
        if m:
            self.hasTrack = True
            self.track = int(m.group(1))

        def get_int(regex, default):
            m = re.search(regex, self.options)
            return int(m.group(1)) if m else default

        def get_str(regex, default):
            m = re.search(regex, self.options)
            return m.group(1) if m else default

        self.startCuts = get_int(r"(\\d+)startcuts(\\s+|,|$)", 0)
        self.startVCuts = get_int(r"(\\d+)startvcuts(\\s+|,|$)", 0)
        self.endCuts = get_int(r"(\\d+)endcuts(\\s+|,|$)", 0)
        self.endVCuts = get_int(r"(\\d+)endvcuts(\\s+|,|$)", 0)
        self.cuts = get_int(r"(\\d+)cuts", 2)
        self.vcuts = get_int(r"(\\d+)vcuts", 1)
        self.routeWidthRule = get_str(r"routeWidth=([^,\\s+,$]+)", "width")
        self.startLayer = get_str(r"startLayer=([^,\\s+,$]+)", "")
        self.stopLayer = get_str(r"stopLayer=([^,\\s+,$]+)", "")

        if self.startLayer:
            for r in self.startRects:
                r.layer = self.startLayer
        if self.stopLayer:
            for r in self.stopRects:
                r.layer = self.stopLayer

        rt = routeType
        if rt == "-|--":
            self.routeType = "LEFT"
        elif rt == "--|-":
            self.routeType = "RIGHT"
            self.leftAlignCut = False
        elif rt == "-":
            self.routeType = "STRAIGHT"
        elif rt == "-|":
            self.routeType = "U_RIGHT"
            self.leftAlignCut = False
        elif rt == "|-":
            self.routeType = "U_LEFT"
        elif rt == "--|":
            self.routeType = "U_TOP"
        elif rt == "|--":
            self.routeType = "U_BOTTOM"
        elif rt == "->":
            self.routeType = "STRAIGHT"
        elif rt == "||":
            self.routeType = "VERTICAL"
        else:
            self.routeType = "ROUTE_UNKNOWN"

        if re.search(r"leftdownleftup", self.options):
            self.routeType = "LEFT_DOWN_LEFT_UP"
        if re.search(r"leftupleftdown", self.options):
            self.routeType = "LEFT_UP_LEFT_DOWN"
        if re.search(r"strap", self.options):
            self.routeType = "STRAP"

    def add(self, child):
        super().add(child)
        if child and (not hasattr(child, 'isCut') or not child.isCut()):
            self.routes.append(child)

    def addMany(self, children):
        for r in children:
            self.add(r)

    def addStartCuts(self):
        if re.search(r"nostartcut", self.options):
            return
        return

    def addEndCuts(self):
        if re.search(r"noendcut", self.options):
            return
        return

    def applyOffset(self, width, rect, offset):
        if offset == "HIGH":
            rect.translate(0, +width)
        elif offset == "LOW":
            rect.translate(0, -width)
        self.updateBoundingRect()

    def route(self):
        start_org = list(self.startRects)
        stop_org = list(self.stopRects)
        self.startRects = [r.getCopy() for r in start_org]
        self.stopRects = [r.getCopy() for r in stop_org]

        self.addStartCuts()
        self.addEndCuts()

        if self.routeType == "LEFT" or self.routeType == "RIGHT":
            self.routeOne()
        elif self.routeType == "STRAIGHT":
            self.routeStraight()
        elif self.routeType == "VERTICAL":
            self.routeVertical()
        elif self.routeType in ("U_RIGHT", "U_LEFT"):
            self.routeU()
        elif self.routeType in ("U_TOP", "U_BOTTOM"):
            self.routeUHorizontal()
        elif self.routeType == "LEFT_DOWN_LEFT_UP":
            self.routeLeftDownLeftUp()
        elif self.routeType == "LEFT_UP_LEFT_DOWN":
            self.routeLeftUpLeftDown()
        elif self.routeType == "STRAP":
            self.routeStrap()

        if len(self.startRects) > 0:
            r = self.startRects[0]
            t = Text(self.name)
            t.moveTo(r.x1, r.y1)
            self.add(t)

    def routeOne(self):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        space = rules.get(self.routeLayer, "space")
        if re.search(r"noSpace", self.options):
            space = -width
        x_left = min(r.x1 for r in self.startRects) if self.startRects else 0
        x_right = max(r.x2 for r in self.startRects) if self.startRects else 0
        hgrid = rules.get("ROUTE", "horizontalgrid")
        x = 0
        if self.routeType == "RIGHT":
            x = x_left - space - width
            if self.hasTrack:
                x = x - hgrid*self.track - space
        elif self.routeType == "LEFT":
            x = x_right + space
            if self.hasTrack:
                x = x + hgrid*self.track + space
        if self.startTrim == "TRIM_START_LEFT":
            for rect in self.startRects:
                rect.setLeft(rect.x2 - 2*width)
        elif self.startTrim == "TRIM_START_RIGHT":
            for rect in self.startRects:
                rect.setRight(rect.x1 + 2*width)
        if self.endTrim == "TRIM_END_LEFT":
            for rect in self.stopRects:
                rect.setLeft(rect.x2 - 2*width)
        elif self.endTrim == "TRIM_END_RIGHT":
            for rect in self.stopRects:
                rect.setRight(rect.x1 + 2*width)
        self.addHorizontalTo(x, self.startRects, self.startOffset)
        self.addHorizontalTo(x, self.stopRects, self.stopOffset)
        self.updateBoundingRect()
        self.addVertical(x)
        for r in self.addAfterRoute:
            self.add(r)

    def routeLeftDownLeftUp(self):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        space = rules.get(self.routeLayer, "space")
        x = max(r.x2 for r in self.startRects) + space*2 if self.startRects else 0
        for rect in self.startRects:
            r = Rect(self.routeLayer, rect.x1, rect.y1, x-rect.x1, width)
            self.applyOffset(width, r, self.startOffset)
            self.add(r)
        for rect in self.stopRects:
            x1 = rect.x1
            if x1 > x:
                ra = Rect(self.routeLayer, x, rect.y1-space-width, x1-x, width)
            else:
                ra = Rect(self.routeLayer, x1, rect.y1-space-width, x-x1, width)
            rb = Rect(self.routeLayer, ra.x2-width, ra.y1, width, rect.y2 - ra.y1)
            self.add(ra)
            self.add(rb)
        self.updateBoundingRect()
        r = Rect(self.routeLayer, x, self.y1, width, self.height())
        self.add(r)

    def routeLeftUpLeftDown(self):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        space = rules.get(self.routeLayer, "space")
        x = max(r.x2 for r in self.startRects) + space*2 if self.startRects else 0
        y = 0
        for rect in self.startRects:
            r = Rect(self.routeLayer, rect.x1, rect.y1, x-rect.x1, width)
            self.applyOffset(width, r, self.startOffset)
            self.add(r)
            rc = Rect(self.routeLayer, r.x2, r.y1, width, space+width)
            self.add(rc)
            if rc.y2 > y:
                y = rc.y2
        for rect in self.stopRects:
            x1 = rect.x1
            if x1 > x:
                ra = Rect(self.routeLayer, x, y, x1-x, width)
            else:
                ra = Rect(self.routeLayer, x1, y, x-x1, width)
            rb = Rect(self.routeLayer, rect.x1-width, rect.y1, width, ra.y2 - rect.y1)
            self.add(ra)
            self.add(rb)
        self.updateBoundingRect()

    def routeStrap(self):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        vertical = re.search(r"vertical(,|\\s+|$)", self.options) is not None
        if vertical:
            if len(self.startRects) == 1:
                sr = self.startRects[0]
                for r in self.stopRects:
                    rc = Rect(self.routeLayer, r.x1, sr.y1, width, r.y1 - sr.y1)
                    self.add(rc)
        else:
            if len(self.startRects) == 1:
                sr = self.startRects[0]
                for r in self.stopRects:
                    rc = Rect(self.routeLayer, sr.x1, r.y1, r.x1 - sr.x1, width)
                    self.add(rc)
            elif len(self.stopRects) == 1:
                sr = self.stopRects[0]
                for r in self.startRects:
                    rc = Rect(self.routeLayer, r.x2, r.y1, sr.x2 - r.x2, width)
                    self.add(rc)

    def addVertical(self, x):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        if re.search(r"novert", self.options):
            return
        if len(self.routes) == 0:
            return
        y1_m = min(r.y1 for r in self.routes)
        y2_m = max(r.y2 for r in self.routes)
        r = VerticalRectangleFromTo(self.routeLayer, x, y1_m, y2_m, width)
        if r:
            self.add(r)

    def routeVertical(self):
        if not (len(self.startRects) > 0 and len(self.stopRects) > 0):
            return
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        yc = min(min(r.y1 for r in self.startRects), min(r.y1 for r in self.stopRects))
        height = max(r.y2 for r in self.stopRects) - yc
        xc = int(min(r.centerX() for r in self.startRects)) - int(width/2)
        r = Rect(self.routeLayer, xc, yc, width, height)
        self.add(r)

    def routeStraight(self):
        if len(self.startRects) == len(self.stopRects):
            count = len(self.startRects)
            for x in range(count):
                r1 = self.startRects[x]
                r2 = self.stopRects[x]
                height = min(r1.height(), r2.height())
                center = r1.centerY()
                r = Rect(self.routeLayer, r1.x1, center - height/2.0, r2.x2 - r1.x1, height)
                self.add(r)
        elif len(self.startRects) == 1:
            r1 = self.startRects[0]
            for r2 in self.stopRects:
                height = min(r1.height(), r2.height())
                center = r1.centerY()
                r = Rect(self.routeLayer, r1.x1, center - height/2.0, r2.x2 - r1.x1, height)
                self.add(r)

    def addHorizontalTo(self, x, rects, offset):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        minwidth = width
        try:
            minwidth = rules.get(self.routeLayer, "minwidth")
        except Exception:
            pass
        for r in rects:
            if offset in ("HIGH", "LOW"):
                x1 = r.centerX()
                if x1 < x:
                    rect1 = HorizontalRectangleFromTo(self.routeLayer, r.centerX(), r.x2, r.y1, width)
                    rect2 = HorizontalRectangleFromTo(self.routeLayer, r.x2 - minwidth, x, r.y1, width)
                    if rect1 and rect2:
                        self.addAfterRoute.append(rect1)
                        self.add(rect2)
                        self.applyOffset(width, rect2, offset)
                else:
                    rect1 = HorizontalRectangleFromTo(self.routeLayer, r.x1, r.centerX(), r.y1, width)
                    rect2 = HorizontalRectangleFromTo(self.routeLayer, r.x1 + minwidth, x, r.y1, width)
                    if rect1 and rect2:
                        self.addAfterRoute.append(rect1)
                        self.add(rect2)
                        self.applyOffset(width, rect2, offset)
            else:
                rect = HorizontalRectangleFromTo(self.routeLayer, r.centerX(), x, r.y1, width)
                if rect:
                    self.add(rect)
