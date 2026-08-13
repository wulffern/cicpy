######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2026-8-13
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
"""Nets that travel together, told once.

Four bias currents leave one block and cross a tile to reach another.
As four Paths that is the same story written four times, with the
lane index of each one carried by hand -- and the moment the corridor
moves, all four move by hand too.

A BUS IS A PATH. Every anchor already takes an offset (`anchor +
2 * p.PITCH`), which is exactly what separates one member of a bundle
from the next, so a Bus is the same steps with the index applied: step
`k` of member `i` aims at the same anchor, `i` lanes over. The bundle
stays parallel through every turn because a turn is two anchored moves
and both are offset.

Where the bundle ends and the nets go their own ways, the members are
Paths like any other::

    b = cell.bus(nets, "M5", starts=pins, lanes=2)
    b.start()
    b.movey(b.track("cband", 2))     # four rows, two lanes apart
    b.movex(b.track("dband", 1))     # east, still parallel

    p = b.member("IBP_1U<0>")        # and this one alone from here
    p.down("M2")
    p.movey(p.landing("y"))
    p.end()
"""
import copy
import logging

from .path import Path

log = logging.getLogger("Bus")


class Bus(Path):
    """Several nets on parallel lanes, one story."""

    def __init__(self, nets, layer, starts=None, stops=None,
                 options="", lanes=1):
        super().__init__(",".join(nets), layer, [], [], options)
        self.nets = list(nets)
        #- HOW FAR APART THE MEMBERS RUN, in legal lanes. One is as
        #- close as the technology allows for the WIRES, and a bundle
        #- that turns needs more: the via pad at a turn is three times
        #- the wire, so four members turning one lane apart leave 2400
        #- between their pads where met4.2 wants 3000.
        self.lanes = max(1, int(lanes))
        starts = list(starts or [])
        stops = list(stops or [])
        self.members = []
        for i, net in enumerate(self.nets):
            m = Path(net, layer,
                     [starts[i]] if i < len(starts) else [],
                     [stops[i]] if i < len(stops) else [],
                     options)
            self.members.append(m)

    def member(self, net):
        """One net's own path, to be continued alone."""
        for m in self.members:
            if m.net == net:
                return m
        log.error(f"{self.net}: no member {net!r}")
        return None

    #- -- the whole point ---------------------------------------------
    def _add(self, step):
        """Every member takes this step, `i` lanes over.

        A step with no anchor -- start, end, up, down -- is the same
        for all of them; a step that aims somewhere is aimed one lane
        further for each member.
        """
        for i, m in enumerate(self.members):
            m._add(self._lane(step, i))
        return self

    def _lane(self, step, i):
        s = copy.copy(step)
        anchor = getattr(s, "anchor", None)
        if i and anchor is not None:
            s.anchor = anchor + (i * self.lanes) * self.PITCH
        return s

    def route(self):
        """Nothing: the MEMBERS are the routes.

        A Bus is the shape of a bundle, not a thing that gets drawn.
        Its members are registered with the cell like any other route,
        so the route phase walks them, the writers serialise them and
        every tool that reads a .cic sees them. Held as children of
        the Bus instead they drew fine and appeared nowhere -- the
        geometry was in the GDS and the .cic had none of it, so
        checkroutes, tracks and render were all blind to the one
        bundle in the cell.
        """
        return
