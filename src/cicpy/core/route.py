
from .cell import Cell
from .rect import Rect, HorizontalRectangleFromTo, VerticalRectangleFromTo, sortLeftOnTop, sortRightOnTop, sortBottomOnTop, sortTopOnTop
from .text import Text
from .rules import Rules
from .cut import Cut
import re
import logging


def _option_int(options, name):
    m = re.search(rf"(^|[,\s]){re.escape(name)}([+-]?\d+)(?=,|\s|$)", options or "")
    return int(m.group(2)) if m else None


class Route(Cell):

    def __init__(self, net, layer, start, stop, options, routeType):
        super().__init__(net)
        self.log = logging.getLogger("Route")
        self.routeLayer = layer
        self.routeType = "ROUTE_UNKNOWN"
        self.route_ = routeType
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
        self.startCutRects = list()
        self.endCutRects = list()
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

        if re.search(r"onTopR", self.options):
            sortRightOnTop(self.startRects)
            sortRightOnTop(self.stopRects)
        elif re.search(r"onTopB", self.options):
            sortBottomOnTop(self.startRects)
            sortBottomOnTop(self.stopRects)
        elif re.search(r"onTopT", self.options):
            sortTopOnTop(self.startRects)
            sortTopOnTop(self.stopRects)
        else:
            sortLeftOnTop(self.startRects)
            sortLeftOnTop(self.stopRects)

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

        track = _option_int(self.options, "track")
        if track is not None:
            self.hasTrack = True
            self.track = track

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

    def _route_owner_info(self):
        return {
            "name": getattr(self, "name", ""),
            "net": getattr(self, "net", ""),
            "layer": getattr(self, "routeLayer", ""),
            "route": getattr(self, "route_", ""),
            "options": getattr(self, "options", ""),
            "debug_api": getattr(self, "debug_api", ""),
            "debug_callsite": getattr(self, "debug_callsite", ""),
            "debug_command": getattr(self, "debug_command", ""),
        }

    def add(self, child):
        if child is not None and hasattr(child, "isRect") and child.isRect():
            if not getattr(child, "net", ""):
                child.net = self.net
            child.route_owner = self
            child.route_owner_info = self._route_owner_info()
        super().add(child)
        if child and (not hasattr(child, 'isCut') or not child.isCut()):
            self.routes.append(child)

    def _candidateVerticalRect(self, x):
        if len(self.startRects) == 0 and len(self.stopRects) == 0:
            return None
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        y1 = min([r.y1 for r in self.startRects + self.stopRects])
        y2 = max([r.y2 for r in self.startRects + self.stopRects])
        return VerticalRectangleFromTo(self.routeLayer, x, y1, y2, width)

    def _shiftRect(self, rect, dx, dy):
        rr = rect.getCopy()
        rr.translate(dx, dy)
        return rr

    def _segmentsForCandidate(self, x):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        minwidth = width
        try:
            minwidth = rules.get(self.routeLayer, "minwidth")
        except Exception:
            pass

        segments = []
        vrect = self._candidateVerticalRect(x)
        if vrect:
            segments.append(vrect)

        def add_hsegments(rects, offset):
            for r in rects:
                shifted = self._shiftRect(r, 0, 0)
                if offset in ("HIGH", "LOW"):
                    x1 = shifted.centerX()
                    if x1 < x:
                        rect1 = HorizontalRectangleFromTo(self.routeLayer, shifted.centerX(), shifted.x2, shifted.y1, width)
                        rect2 = HorizontalRectangleFromTo(self.routeLayer, shifted.x2 - minwidth, x, shifted.y1, width)
                        if rect1:
                            segments.append(rect1)
                        if rect2:
                            if offset == "HIGH":
                                rect2.translate(0, width)
                            elif offset == "LOW":
                                rect2.translate(0, -width)
                            segments.append(rect2)
                    else:
                        rect1 = HorizontalRectangleFromTo(self.routeLayer, shifted.x1, shifted.centerX(), shifted.y1, width)
                        rect2 = HorizontalRectangleFromTo(self.routeLayer, x, shifted.x1 + minwidth, shifted.y1, width)
                        if rect1:
                            segments.append(rect1)
                        if rect2:
                            if offset == "HIGH":
                                rect2.translate(0, width)
                            elif offset == "LOW":
                                rect2.translate(0, -width)
                            segments.append(rect2)
                else:
                    hrect = HorizontalRectangleFromTo(self.routeLayer, shifted.centerX(), x, shifted.centerY() - width/2, width)
                    if hrect:
                        segments.append(hrect)

        add_hsegments(self.startRects, self.startOffset)
        add_hsegments(self.stopRects, self.stopOffset)
        return segments

    def _isCandidateBlocked(self, x):
        parent = getattr(self, "parent", None)
        if parent is None or not hasattr(parent, "getOccupiedRectangles"):
            return False

        rules = Rules.getInstance()
        space = rules.get(self.routeLayer, "space")
        blocked = []
        if re.search(r"(avoidblocks)(,|\s+|$)", self.options or ""):
            blocked.extend(parent.getOccupiedRectangles(self.routeLayer, ignoreNet=self.net))
        if re.search(r"(avoidboundaries|blockboundaries)(,|\s+|$)", self.options or ""):
            blocked.extend(parent.getOccupiedRectangles(self.routeLayer, ignoreNet=self.net, includeBoundaries=True))
        if re.search(r"(avoidkeepouts|blockkeepouts)(,|\s+|$)", self.options or "") and hasattr(parent, "getRouteKeepouts"):
            keepout_filter = ""
            m = re.search(r"keepout=([^,\s]+)", self.options or "")
            if m:
                keepout_filter = m.group(1)
            blocked.extend(parent.getRouteKeepouts(self.routeLayer, keepout_filter))
        if len(blocked) == 0:
            return False
        for segment in self._segmentsForCandidate(x):
            test_rect = segment.getCopy()
            test_rect.adjust(-space, -space, space, space)
            for occ in blocked:
                if test_rect.overlaps(occ):
                    return True
        return False

    def _find_unblocked_x(self, x, step, prefer_negative=False, search_limit=32):
        if step == 0 or not re.search(r"(avoidblocks|avoidboundaries|blockboundaries|avoidkeepouts|blockkeepouts)(,|\s+|$)", self.options or ""):
            return x
        if not self._isCandidateBlocked(x):
            return x
        directions = [-1, 1] if prefer_negative else [1, -1]
        for idx in range(1, search_limit + 1):
            for direction in directions:
                candidate = x + direction * idx * step
                if not self._isCandidateBlocked(candidate):
                    return candidate
        return x

    def addMany(self, children):
        for r in children:
            self.add(r)

    def _allowedCutCounts(self, hcuts, vcuts):
        hcuts = int(hcuts)
        vcuts = int(vcuts)
        if vcuts > hcuts:
            return (1, 2)
        return (2, 1)

    def _addCuts(self, rects, allcuts, hcuts, vcuts):
        if self.routeLayer == "PO":
            return []
        default_hcuts, default_vcuts = self._allowedCutCounts(hcuts, vcuts)
        cuts = []
        for rect in rects:
            if rect is None or self.routeLayer == rect.layer:
                continue

            cut_h = default_hcuts
            cut_v = default_vcuts
            if self.fillhcut and rect.isHorizontal():
                cut_h, cut_v = (2, 1)
            elif self.fillvcut and rect.isVertical():
                cut_h, cut_v = (1, 2)

            insts = Cut.getCutsForRects(self.routeLayer, [rect], cut_h, cut_v, self.leftAlignCut)
            inst = insts[0] if insts else None
            if inst is not None:
                cuts.append(inst)
                allcuts.append(inst)
        return cuts

    def addStartCuts(self):
        if re.search(r"nostartcut", self.options):
            return

        lcuts = self.startCuts if self.startCuts > 0 else self.cuts
        lvcuts = self.startVCuts if self.startVCuts > 0 else self.vcuts
        cuts = self._addCuts(self.startRects, self.startCutRects, lcuts, lvcuts)

        if self.startOffsetCut == "HIGH":
            for cut in cuts:
                cut.translate(0, cut.height() / 2)
            for rect in self.startRects:
                rect.translate(0, rect.height() / 2)
        elif self.startOffsetCut == "LOW":
            for cut in cuts:
                cut.translate(0, -cut.height() / 2)
            for rect in self.startRects:
                rect.translate(0, -rect.height() / 2)

        self.addMany(cuts)

    def addEndCuts(self):
        if re.search(r"noendcut", self.options):
            return

        lcuts = self.endCuts if self.endCuts > 0 else self.cuts
        lvcuts = self.endVCuts if self.endVCuts > 0 else self.vcuts
        cuts = self._addCuts(self.stopRects, self.endCutRects, lcuts, lvcuts)

        if self.endOffsetCut == "HIGH":
            for cut in cuts:
                cut.translate(0, cut.height() / 2)
            for rect in self.stopRects:
                rect.translate(0, rect.height() / 2)
        elif self.endOffsetCut == "LOW":
            for cut in cuts:
                cut.translate(0, -cut.height() / 2)
            for rect in self.stopRects:
                rect.translate(0, -rect.height() / 2)

        self.addMany(cuts)

    def applyOffset(self, width, rect, offset):
        if offset == "HIGH":
            rect.translate(0, +width)
        elif offset == "LOW":
            rect.translate(0, -width)
        self.updateBoundingRect()

    def route(self):
        self.log.info(f"route() called: net={self.net}, layer={self.routeLayer}, routeType={self.routeType}, route={self.route_}, options={self.options}")
        
        # Take a copy of all route rects to ensure we don't change the originals
        start_rects_org = self.startRects
        stop_rects_org = self.stopRects
        self.startRects = []
        self.stopRects = []
        
        for r in start_rects_org:
            self.startRects.append(r.getCopy())
        for r in stop_rects_org:
            self.stopRects.append(r.getCopy())

        self.log.info(f"  startRects count: {len(self.startRects)}, stopRects count: {len(self.stopRects)}")

        # TODO: To make it horribly confusing, it matters for the routing which
        # sequence the cuts are added. Should they be added first, or after.
        #
        # For LEFT/RIGHT routes, the bounding box for routing will include the
        # cuts, which may lead to an extra nub on the routes
        #
        # If the cuts are added after, then the routing might not reach the cuts.

        self.addStartCuts()
        self.addEndCuts()

        # Route based on routeType
        if self.routeType == "LEFT":
            self.log.info(f"  Routing with: routeOne()")
            self.routeOne()
        elif self.routeType == "RIGHT":
            self.log.info(f"  Routing with: routeOne()")
            self.routeOne()
        elif self.routeType == "STRAIGHT":
            self.log.info(f"  Routing with: routeStraight()")
            self.routeStraight()
        elif self.routeType == "VERTICAL":
            self.log.info(f"  Routing with: routeVertical()")
            self.routeVertical()
        elif self.routeType == "U_RIGHT":
            self.log.info(f"  Routing with: routeU()")
            self.routeU()
        elif self.routeType == "U_LEFT":
            self.log.info(f"  Routing with: routeU()")
            self.routeU()
        elif self.routeType == "U_TOP":
            self.log.info(f"  Routing with: routeUHorizontal()")
            self.routeUHorizontal()
        elif self.routeType == "U_BOTTOM":
            self.log.info(f"  Routing with: routeUHorizontal()")
            self.routeUHorizontal()
        elif self.routeType == "LEFT_DOWN_LEFT_UP":
            self.log.info(f"  Routing with: routeLeftDownLeftUp()")
            self.routeLeftDownLeftUp()
        elif self.routeType == "LEFT_UP_LEFT_DOWN":
            self.log.info(f"  Routing with: routeLeftUpLeftDown()")
            self.routeLeftUpLeftDown()
        elif self.routeType == "STRAP":
            self.log.info(f"  Routing with: routeStrap()")
            self.routeStrap()
        else:
            self.log.error(f"Error(route.py): Unknown route routeType={self.route_} net={self.net} layer={self.routeLayer} options={self.options}")

        if len(self.startRects) > 0 and not re.search(r"nolabel(,|\s+|$)", self.options):
            r = self.startRects[0]
            t = Text(self.name)
            t.moveTo(r.x1, r.y1)
            self.add(t)


    def routeOne(self):
        self.log.info(f"routeOne: net={self.net}, layer={self.routeLayer}, route={self.route_}, options={self.options}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        
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
            x = self._find_unblocked_x(x, hgrid, prefer_negative=True)
        elif self.routeType == "LEFT":
            x = x_right + space
            if self.hasTrack:
                x = x + hgrid*self.track + space
            x = self._find_unblocked_x(x, hgrid, prefer_negative=False)
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
        self.log.info(f"routeLeftDownLeftUp: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        
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
        self.log.info(f"routeLeftUpLeftDown: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        
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
        self.log.info(f"routeStrap: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}, options={self.options}")
        
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
            self.log.warning(f"addVertical: No routes found for net {self.net}, cannot create vertical connection")
            return

        from .cell import Cell
        route_bound = Cell.calcBoundingRectFromList(self.routes)
        y1_m = route_bound.y1
        y2_m = route_bound.y2

        if self.antenna:
            next1 = rules.getNextLayer(self.routeLayer)
            next2 = rules.getNextLayer(next1) if next1 else ""
            if next2:
                c1 = Cut.getInstance(self.routeLayer, next2, 1, 2)
                c2 = Cut.getInstance(self.routeLayer, next2, 1, 2)
                if c1 and c2 and (y2_m - y1_m) > (c1.height() * 2 + width * 2):
                    r = Rect(next2, x, y1_m, width, y2_m - y1_m)
                    c1.moveTo(x, y1_m)
                    c2.moveTo(x, r.y2 - c2.height())
                    self.add(c1)
                    self.add(c2)
                    self.add(r)
                    return

        r = VerticalRectangleFromTo(self.routeLayer, x, y1_m, y2_m, width)
        if r:
            self.add(r)


    def routeVertical(self):
        self.log.info(f"routeVertical: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        
        if not (len(self.startRects) > 0 and len(self.stopRects) > 0):
            return
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)

        def connection_center(r1, r2):
            overlap_left = max(r1.x1, r2.x1)
            overlap_right = min(r1.x2, r2.x2)
            if overlap_left <= overlap_right:
                return int((overlap_left + overlap_right) / 2)
            return int(r1.centerX())

        def add_connection(r1, r2, start_cut=None, end_cut=None):
            xc_center = connection_center(r1, r2)
            if start_cut is not None:
                start_cut.moveCenter(xc_center, start_cut.centerY())
            if end_cut is not None:
                end_cut.moveCenter(xc_center, end_cut.centerY())
            r = VerticalRectangleFromTo(self.routeLayer, xc_center - int(width / 2), r1.centerY(), r2.centerY(), width)
            if r:
                self.add(r)

        if len(self.startRects) == len(self.stopRects):
            for idx, (r1, r2) in enumerate(zip(self.startRects, self.stopRects)):
                start_cut = self.startCutRects[idx] if idx < len(self.startCutRects) else None
                end_cut = self.endCutRects[idx] if idx < len(self.endCutRects) else None
                add_connection(r1, r2, start_cut, end_cut)
        elif len(self.startRects) == 1:
            r1 = self.startRects[0]
            start_cut = self.startCutRects[0] if len(self.startCutRects) > 0 else None
            for idx, r2 in enumerate(self.stopRects):
                end_cut = self.endCutRects[idx] if idx < len(self.endCutRects) else None
                add_connection(r1, r2, start_cut, end_cut)
        elif len(self.stopRects) == 1:
            r2 = self.stopRects[0]
            end_cut = self.endCutRects[0] if len(self.endCutRects) > 0 else None
            for idx, r1 in enumerate(self.startRects):
                start_cut = self.startCutRects[idx] if idx < len(self.startCutRects) else None
                add_connection(r1, r2, start_cut, end_cut)


    def routeStraight(self):
        self.log.info(f"routeStraight: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        
        if len(self.startRects) == len(self.stopRects):
            count = len(self.startRects)
            for x in range(count):
                r1 = self.startRects[x]
                r2 = self.stopRects[x]
                height = min(r1.height(), r2.height())
                center = r1.centerY()
                r = Rect(self.routeLayer, r1.x1, center - height/2.0, r2.x2 - r1.x1, height)
                self.add(r)
                if x < len(self.endCutRects):
                    self.endCutRects[x].moveCenter(r2.centerX(), center)
        elif len(self.startRects) == 1:
            r1 = self.startRects[0]
            for idx, r2 in enumerate(self.stopRects):
                height = min(r1.height(), r2.height())
                center = r1.centerY()
                r = Rect(self.routeLayer, r1.x1, center - height/2.0, r2.x2 - r1.x1, height)
                self.add(r)
                if idx < len(self.endCutRects):
                    self.endCutRects[idx].moveCenter(r2.centerX(), center)


    def routeUHorizontal(self):
        self.log.info(f"routeUHorizontal: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        space = rules.get(self.routeLayer, "space")
        vgrid = rules.get("ROUTE", "verticalgrid")

        allrect = self.startRects + self.stopRects
        if len(allrect) == 0:
            return

        all_bound = Cell.calcBoundingRectFromList(allrect)
        y = 0
        if self.routeType == "U_TOP":
            y = all_bound.top() + space
            if self.hasTrack:
                y = y + vgrid * self.track + space
        elif self.routeType == "U_BOTTOM":
            y = all_bound.bottom() - space - width
            if self.hasTrack:
                y = y - vgrid * self.track - space
        else:
            self.log.error(f"Unknown U horizontal route type: {self.routeType}")
            return

        rect = HorizontalRectangleFromTo(self.routeLayer, all_bound.left(), all_bound.right(), y, width)
        if rect:
            self.add(rect)

        for r in allrect:
            ra = None
            if self.routeType == "U_BOTTOM":
                ra = VerticalRectangleFromTo(self.routeLayer, r.x1 - width, rect.y1, r.y2, width)
            elif self.routeType == "U_TOP":
                ra = VerticalRectangleFromTo(self.routeLayer, r.x1 - width, r.y1, rect.y2, width)
            if ra:
                self.add(ra)
        self.updateBoundingRect()


    def routeU(self):
        self.log.info(f"routeU: net={self.net}, layer={self.routeLayer}, startRects={len(self.startRects)}, stopRects={len(self.stopRects)}")
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        space = rules.get(self.routeLayer, "space")
        hgrid = rules.get("ROUTE", "horizontalgrid")

        allrect = self.startRects + self.stopRects
        if len(allrect) == 0:
            return

        all_bound = Cell.calcBoundingRectFromList(allrect)
        x = 0
        if self.routeType == "U_RIGHT":
            x = all_bound.right() + space
            if self.hasTrack:
                x = x + hgrid * self.track + space
            x = self._find_unblocked_x(x, hgrid, prefer_negative=False)
        elif self.routeType == "U_LEFT":
            x = all_bound.left() - space - width
            if self.hasTrack:
                x = x - hgrid * self.track - space
            x = self._find_unblocked_x(x, hgrid, prefer_negative=True)
        else:
            self.log.error(f"Unknown U route type: {self.routeType}")
            return

        self.addHorizontalTo(x, self.startRects, self.startOffset)
        self.addHorizontalTo(x, self.stopRects, self.stopOffset)
        self.updateBoundingRect()
        self.addVertical(x)


    def addHorizontalTo(self, x, rects, offset):
        rules = Rules.getInstance()
        width = rules.get(self.routeLayer, self.routeWidthRule)
        minwidth = width
        try:
            minwidth = rules.get(self.routeLayer, "minwidth")
        except Exception as e:
            self.log.debug(f"No minwidth rule for layer {self.routeLayer}, using width: {e}")
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

class OrthogonalLayerRoute(Route):

    def __init__(self, net, vertical_layer, horizontal_layer, access_rects, options="", cuts=1):
        Cell.__init__(self, net)
        self.log = logging.getLogger("OrthogonalLayerRoute")
        self.net = net
        self.verticalLayer = vertical_layer
        self.horizontalLayer = horizontal_layer
        self.accessRects = list(access_rects or [])
        self.options = options or ""
        self.routes = list()
        self.cuts = cuts
        self.hasTrack = False
        self.track = 0
        self.hasBranchTrack = False
        self.branchTrack = 0
        self.trackDirection = +1
        self.anchorMode = "bbox"
        if re.search(r"(^|[ ,])left([ ,]|$)", self.options):
            self.trackDirection = -1
        elif re.search(r"(^|[ ,])right([ ,]|$)", self.options):
            self.trackDirection = +1
        elif re.search(r"(^|[ ,])(center|balanced)([ ,]|$)", self.options):
            self.trackDirection = 0

        if re.search(r"onTopRight(,|\s+|$)", self.options):
            self.anchorMode = "right"
        elif re.search(r"onTopLeft(,|\s+|$)", self.options):
            self.anchorMode = "left"
        elif re.search(r"onTopTop(,|\s+|$)", self.options):
            self.anchorMode = "top"
        elif re.search(r"onTopBottom(,|\s+|$)", self.options):
            self.anchorMode = "bottom"
        track = _option_int(self.options, "track")
        if track is not None:
            self.hasTrack = True
            self.track = track
        branch_track = _option_int(self.options, "branchtrack")
        if branch_track is not None:
            self.hasBranchTrack = True
            self.branchTrack = branch_track
        m = re.search(r"routeWidth=([^,\s+,$]+)", self.options)
        self.routeWidthRule = m.group(1) if m else "width"

    def _route_owner_info(self):
        return {
            "name": getattr(self, "name", ""),
            "net": getattr(self, "net", ""),
            "layer": f"{getattr(self, 'verticalLayer', '')}/{getattr(self, 'horizontalLayer', '')}",
            "route": "orthogonal",
            "options": getattr(self, "options", ""),
            "debug_api": getattr(self, "debug_api", ""),
            "debug_callsite": getattr(self, "debug_callsite", ""),
            "debug_command": getattr(self, "debug_command", ""),
        }

    def _rects_touch_or_overlap(self, rect1, rect2):
        if rect1 is None or rect2 is None:
            return False
        if rect1.x2 < rect2.x1 or rect2.x2 < rect1.x1:
            return False
        if rect1.y2 < rect2.y1 or rect2.y2 < rect1.y1:
            return False
        return True

    def _layers_directly_connect(self, layer1, layer2):
        if layer1 == layer2:
            return True
        rules = Rules.getInstance()
        if rules is None:
            return False
        layer_obj_1 = rules.getLayer(layer1)
        layer_obj_2 = rules.getLayer(layer2)
        if layer_obj_1 is None or layer_obj_2 is None:
            return False
        if getattr(layer_obj_1, "next", "") == layer2:
            return True
        if getattr(layer_obj_1, "previous", "") == layer2:
            return True
        if getattr(layer_obj_2, "next", "") == layer1:
            return True
        if getattr(layer_obj_2, "previous", "") == layer1:
            return True
        return False

    def _collapse_access_rects(self):
        collapsed = []
        seen = set()
        for rect in self.accessRects:
            if rect is None:
                continue
            key = (rect.layer, rect.x1, rect.y1, rect.x2, rect.y2)
            if key in seen:
                continue
            seen.add(key)
            collapsed.append(rect)
        collapsed.sort(key=lambda r: (r.centerY(), r.centerX(), r.x1))
        return collapsed

    def _cut_shape_for_rect(self, rect):
        count = max(2, int(getattr(self, "cuts", 2)))
        if rect.height() >= rect.width():
            return (1, count)
        return (count, 1)

    def _anchor_sorted_access_rects(self, rects):
        ordered = list(rects)
        if self.anchorMode == "left":
            sortLeftOnTop(ordered)
        elif self.anchorMode == "right":
            sortRightOnTop(ordered)
        elif self.anchorMode == "top":
            sortTopOnTop(ordered)
        elif self.anchorMode == "bottom":
            sortBottomOnTop(ordered)
        return ordered

    def _trunk_anchor_rect(self):
        if not self.accessRects:
            return None
        ordered = self._anchor_sorted_access_rects(self.accessRects)
        if ordered:
            return ordered[0]
        return self.accessRects[0]

    def _instantiate_cut(self, layer1, layer2, hcuts, vcuts, xc, yc):
        cut = Cut.getInstance(layer1, layer2, hcuts, vcuts)
        if cut is None:
            cut = Cut.getInstance(layer2, layer1, hcuts, vcuts)
        if cut is None:
            cut = Cut.getInstance(layer1, layer2, vcuts, hcuts)
        if cut is None:
            cut = Cut.getInstance(layer2, layer1, vcuts, hcuts)
        if cut is None:
            return None
        cut.moveCenter(xc, yc)
        return cut

    def _instantiate_cut_on_rect_x(self, route_layer, rect, hcuts, vcuts, yc, left_align=True):
        if rect is None or route_layer == rect.layer:
            return None
        cut = Cut.getInstance(route_layer, rect.layer, hcuts, vcuts)
        if cut is None:
            cut = Cut.getInstance(rect.layer, route_layer, hcuts, vcuts)
        if cut is None:
            cut = Cut.getInstance(route_layer, rect.layer, vcuts, hcuts)
        if cut is None:
            cut = Cut.getInstance(rect.layer, route_layer, vcuts, hcuts)
        if cut is None:
            return None
        if (rect.isVertical() and cut.isHorizontal()) or (rect.isHorizontal() and cut.isVertical()):
            cut = Cut.getInstance(route_layer, rect.layer, vcuts, hcuts)
            if cut is None:
                cut = Cut.getInstance(rect.layer, route_layer, vcuts, hcuts)
        if cut is None:
            return None
        x = rect.x1 if left_align else rect.x2 - cut.width()
        y = yc - cut.height() / 2
        cut.moveTo(x, y)
        return cut

    def _translated_cut_rects(self, cut_inst, layer):
        cell = getattr(cut_inst, "_cell_obj", None)
        rects = []
        if cell is None:
            return rects
        for child in cell.children:
            if child is None or not child.isRect() or child.layer != layer:
                continue
            rr = child.getCopy()
            rr.translate(cut_inst.x1, cut_inst.y1)
            rects.append(rr)
        return rects

    def _connect_pads_with_horizontal(self, left_pad, right_pad, height):
        if left_pad.centerX() <= right_pad.centerX():
            x1 = left_pad.x2
            x2 = right_pad.x1
        else:
            x1 = left_pad.x1
            x2 = right_pad.x2
        return HorizontalRectangleFromTo(
            self.horizontalLayer,
            x1,
            x2,
            left_pad.centerY() - height / 2,
            height,
        )

    def _connect_pads_with_vertical(self, lower_pad, upper_pad, width):
        if lower_pad.centerY() <= upper_pad.centerY():
            y1 = lower_pad.y2
            y2 = upper_pad.y1
        else:
            y1 = upper_pad.y2
            y2 = lower_pad.y1
        return VerticalRectangleFromTo(
            self.verticalLayer,
            lower_pad.centerX(),
            y1,
            y2,
            width,
        )

    def _branch_band_y(self):
        if not self.accessRects:
            return 0
        if not self.hasBranchTrack:
            return None
        rules = Rules.getInstance()
        vgrid = rules.get("ROUTE", "verticalgrid")
        base_y = min(rect.centerY() for rect in self.accessRects)
        return base_y + self.branchTrack * vgrid

    def _trunk_rect(self, x):
        if len(self.accessRects) == 0:
            return None
        rules = Rules.getInstance()
        width = rules.get(self.verticalLayer, self.routeWidthRule)
        y1 = min(rect.y1 for rect in self.accessRects)
        y2 = max(rect.y2 for rect in self.accessRects)
        return VerticalRectangleFromTo(self.verticalLayer, x, y1, y2, width)

    def route(self):
        self.accessRects = self._collapse_access_rects()
        if len(self.accessRects) == 0:
            return
        if len(self.accessRects) == 1:
            if not re.search(r"nolabel(,|\s+|$)", self.options):
                r = self.accessRects[0]
                t = Text(self.name)
                t.moveTo(r.x1, r.y1)
                self.add(t)
            return

        rules = Rules.getInstance()
        vspace = rules.get(self.verticalLayer, "space")
        vwidth = rules.get(self.verticalLayer, self.routeWidthRule)
        hgrid = rules.get("ROUTE", "horizontalgrid")
        x_right = max(rect.x2 for rect in self.accessRects)
        x_left = min(rect.x1 for rect in self.accessRects)
        anchor_rect = self._trunk_anchor_rect() if self.anchorMode != "bbox" else None
        anchor_left = anchor_rect.x1 if anchor_rect is not None else x_left
        anchor_right = anchor_rect.x2 if anchor_rect is not None else x_right
        if self.trackDirection < 0:
            if self.hasTrack:
                trunk_x = anchor_left - (self.track + 1) * (vspace + vwidth)
            else:
                trunk_x = anchor_left - vspace
        elif self.trackDirection > 0:
            if self.hasTrack:
                trunk_x = anchor_right + (self.track + 1) * vspace + self.track * vwidth
            else:
                trunk_x = anchor_right + vspace
        else:
            trunk_x = 0.5 * (x_left + x_right)
            if self.hasTrack:
                trunk_x += self.track * hgrid
        trunk = self._trunk_rect(trunk_x)

        access_branches = []
        trunk_cuts = []
        branch_band_y = self._branch_band_y()
        vwidth = rules.get(self.verticalLayer, self.routeWidthRule)
        hwidth = rules.get(self.horizontalLayer, self.routeWidthRule)
        for access in self.accessRects:
            branch = HorizontalRectangleFromTo(
                self.horizontalLayer,
                access.centerX(),
                trunk_x,
                access.centerY() - hwidth / 2,
                hwidth,
            )
            hcuts, vcuts = self._cut_shape_for_rect(access)
            if branch_band_y is None:
                access_cut = None
                access_access_pads = []
                if access.layer == self.horizontalLayer:
                    access_route_pad = access.getCopy()
                    access_route_pads = [access_route_pad]
                else:
                    access_cut = self._instantiate_cut(self.horizontalLayer, access.layer, hcuts, vcuts, access.centerX(), access.centerY())
                    access_route_pads = self._translated_cut_rects(access_cut, self.horizontalLayer)
                    access_access_pads = self._translated_cut_rects(access_cut, access.layer)
                    if not access_route_pads:
                        continue
                    access_route_pad = access_route_pads[0]

                trunk_hcuts, trunk_vcuts = self._cut_shape_for_rect(trunk)
                trunk_cut = self._instantiate_cut_on_rect_x(self.horizontalLayer, trunk, trunk_hcuts, trunk_vcuts, access_route_pad.centerY(), True)
                trunk_route_pads = self._translated_cut_rects(trunk_cut, self.horizontalLayer)
                trunk_vertical_pads = self._translated_cut_rects(trunk_cut, self.verticalLayer)
                if not trunk_route_pads:
                    continue
                trunk_route_pad = trunk_route_pads[0]

                if access_access_pads:
                    for rr in access_access_pads:
                        rr.net = self.net
                        self.add(rr)
                for rr in access_route_pads:
                    rr.net = self.net
                    self.add(rr)
                for rr in trunk_route_pads:
                    rr.net = self.net
                    self.add(rr)
                for rr in trunk_vertical_pads:
                    rr.net = self.net
                    self.add(rr)

                branch = self._connect_pads_with_horizontal(access_route_pad, trunk_route_pad, branch.height())
                if branch is not None:
                    branch.net = self.net
                    self.add(branch)
                    access_branches.append(branch)

                if access_cut is not None:
                    self.add(access_cut)
                if trunk_cut is not None:
                    self.add(trunk_cut)
                    trunk_cuts.append(trunk_cut)
                continue

            access_cut = None
            access_vertical_pads = []
            access_access_pads = []
            if access.layer == self.verticalLayer:
                access_vertical_pad = access.getCopy()
                access_vertical_pads = [access_vertical_pad]
            else:
                access_cut = self._instantiate_cut(self.verticalLayer, access.layer, hcuts, vcuts, access.centerX(), access.centerY())
                access_vertical_pads = self._translated_cut_rects(access_cut, self.verticalLayer)
                access_access_pads = self._translated_cut_rects(access_cut, access.layer)
                if not access_vertical_pads:
                    continue
                access_vertical_pad = access_vertical_pads[0]

            branch_hcuts, branch_vcuts = self._cut_shape_for_rect(access_vertical_pad)
            branch_cut = self._instantiate_cut_on_rect_x(self.horizontalLayer, access_vertical_pad, branch_hcuts, branch_vcuts, branch_band_y, True)
            branch_route_pads = self._translated_cut_rects(branch_cut, self.horizontalLayer)
            branch_vertical_pads = self._translated_cut_rects(branch_cut, self.verticalLayer)
            if not branch_route_pads or not branch_vertical_pads:
                continue
            branch_route_pad = branch_route_pads[0]
            branch_vertical_pad = branch_vertical_pads[0]

            trunk_hcuts, trunk_vcuts = self._cut_shape_for_rect(trunk)
            trunk_cut = self._instantiate_cut_on_rect_x(self.horizontalLayer, trunk, trunk_hcuts, trunk_vcuts, branch_route_pad.centerY(), True)
            trunk_route_pads = self._translated_cut_rects(trunk_cut, self.horizontalLayer)
            trunk_vertical_pads = self._translated_cut_rects(trunk_cut, self.verticalLayer)
            if not trunk_route_pads or not trunk_vertical_pads:
                continue
            trunk_route_pad = trunk_route_pads[0]

            if access_access_pads:
                for rr in access_access_pads:
                    rr.net = self.net
                    self.add(rr)
            for rr in access_vertical_pads + branch_route_pads + branch_vertical_pads + trunk_route_pads + trunk_vertical_pads:
                rr.net = self.net
                self.add(rr)

            jog = self._connect_pads_with_vertical(access_vertical_pad, branch_vertical_pad, vwidth)
            if jog is not None:
                jog.net = self.net
                self.add(jog)
            branch = self._connect_pads_with_horizontal(branch_route_pad, trunk_route_pad, branch.height())
            if branch is not None:
                branch.net = self.net
                self.add(branch)
                access_branches.append(branch)

            if access_cut is not None:
                self.add(access_cut)
            self.add(branch_cut)
            self.add(trunk_cut)
            trunk_cuts.append(trunk_cut)

        if trunk is not None:
            trunk.net = self.net
            self.add(trunk)

        if not re.search(r"nolabel(,|\s+|$)", self.options):
            t = Text(self.name)
            t.moveTo(trunk_x, min(rect.y1 for rect in self.accessRects))
            self.add(t)
