# Subcells: generate once, instantiate in the top

Goal: stop laying out a big analog cell as one flat field of devices.
Generate each subcell as a real cell -- its own `.mag`, `.sch`, `.sym`,
its own DRC and LVS -- and have the top instantiate those cells and
route only between their ports.

The top cell should be <SCHEMATIC_NAME>.py, with one class <SCHEMATIC_NAME>.

All subcells should be sub classes of the main class. The subcell class should
in the __init__() function define the parameters

- self.instRegex = r"Regex to match instances of top class to include in
  subcell"
- self.groupName = Name of the group
- For stacks self.addOrder([array of regex to match order])

Any routing in the cell/subcell should use the pattern 

``` 
class top(HierCell):
    class pmos(Stack or other LayoutCell): 
        def __init__():
            self._super()
            self.instRegex = r"^xcal.*"
            
        def beforeRoute(self):
            self.addConnectivityRoute() or other routes
            
    class caps(Stack or other LayoutCell): 
        def __init__():
            self._super()
            self.instRegex = r"^xd.*"
            
        def beforeRoute(self):
            self.addConnectivityRoute() or other routes
    def beforeRoute(self):
        self.addConnectivityRoute() or outher routs 
    
```

# Generation of hiearchy 

The spice file from sch2mag, or spi2mag should be read. As soon as the design is
read, then the HierCell should be triggered in design.py to re-organize the
hierarchy. HierCell will read all class members, and then re-structure the
hierachy, as below. 

for example  a top list 

```spice 

.subckt TOP VBD1 LPI VDD_1V8
xca1<7> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<6> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<5> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<4> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<3> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<2> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<1> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<0> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xd1<9> LPI VDD_1V8 REYATR_CAPX1
xd1<8> LPI VDD_1V8 REYATR_CAPX1
xd1<7> LPI VDD_1V8 REYATR_CAPX1
xd1<6> LPI VDD_1V8 REYATR_CAPX1
xd1<5> LPI VDD_1V8 REYATR_CAPX1
xd1<4> LPI VDD_1V8 REYATR_CAPX1
xd1<3> LPI VDD_1V8 REYATR_CAPX1
xd1<2> LPI VDD_1V8 REYATR_CAPX1
xd1<1> LPI VDD_1V8 REYATR_CAPX1
xd1<0> LPI VDD_1V8 REYATR_CAPX1
.ends
```

To

```spice 

.subckt top VBD1 LPI VDD_1V8
xpmos VBD1 LPI VDD_1V8
xcap LPI VDD_1V8
.ends

.subckt pmos VBD1 LPI VDD_1V8
xca1<7> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<6> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<5> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<4> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<3> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<2> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<1> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
xca1<0> VBD1 LPI VDD_1V8 VDD_1V8 REYATR_PCH_4C5F0
.ends 

.subckt caps LPI VDD_1V8
xd1<9> LPI VDD_1V8 REYATR_CAPX1
xd1<8> LPI VDD_1V8 REYATR_CAPX1
xd1<7> LPI VDD_1V8 REYATR_CAPX1
xd1<6> LPI VDD_1V8 REYATR_CAPX1
xd1<5> LPI VDD_1V8 REYATR_CAPX1
xd1<4> LPI VDD_1V8 REYATR_CAPX1
xd1<3> LPI VDD_1V8 REYATR_CAPX1
xd1<2> LPI VDD_1V8 REYATR_CAPX1
xd1<1> LPI VDD_1V8 REYATR_CAPX1
xd1<0> LPI VDD_1V8 REYATR_CAPX1
.ends
```

Once the ckt hierarchy is organized, then design.py should create cells that
match the subcells. Since they are added to cells[] before the top needs them,
then subcells will be available when top needs them. Subcells will be written
with sch, mag, cic, or whatever is needed, or called, by spi2mag. 



# Rules 

- top.py should never contain custom route code. If that's needed, propose new
  route.py functions, or classes
- Always use either 1x2 or 2x1 cuts (or more). A 1x1 cut is not good enough for
  reliability.
- Never store absolute coordinates, or distances, in python code. We need to
  rely on the rules from tech. We want the routes, and placement to be
  technology independent. 
  
  
# Prototype top cells (some will need modification)

```
lelo_temp_sky130a/design 
    LELOTEMP_OTAR.py
    LELOTEMP_CMP.py
    LELOTEMP_CCMP.py
    LELOTEMP_BIAS_IBP.py 
    LELO_TEMP.py
```


# Goal 

I want AI to most of the time write the top.py, however, I do want it to be easy
for a human to understand and modify. Speed of generation is also important. 


# WHERE THIS STANDS (2026-08-12)

Read this first; the stage sections below are the working record and
several of them describe decisions that were later measured and
changed.

## Shipped and verified

| stage | what |
|---|---|
| 0-2 | fingerprint, the `~` path, `Path` as a `Route` |
| 3 (emitter half) | the router writes an ANCHOR, not a coordinate; all 19 gone from the design files |
| 3b | a channel track is one legal lane (`width + space`) |
| 4, 5 | the hierarchy, in memory: `hierarchy()` splits the netlist and builds a cell per subcell, one pass, one process |
| 7 | `cuts` made honest, framework defaults 2, the maze router's lone-via last resort gone |
| 8 | `promoteInstancePort`; the last typed geometry out of LELOTEMP_BIAS_IBP |
| — | the router splits a net onto two rails when its pins have two shapes; n_load_a and n_load_b need no `beforeRoute` |

**The gate, with declared wires, on every build:**

    CMP 0/match   CCMP 0/match   OTAR 0/match
    BIAS_IBP 8/match   LELO_TEMP 95/"Netlists do not match" (VR1 artefact)

90 unit tests, ten integration suites.

## Open, in the order I would take them

1. **Fresh search is 18 DRC / failed pin matching on OTAR, 66 / failed
   on BIAS_IBP.** This is the number that matters for the Goal -- it is
   what the router produces unattended, and until it approaches the
   declared-wires build the `wires` blocks cannot be regenerated
   without a human reading them. An earlier claim that this gap was
   closed was measurement error; see the correction in Stage 3.
   Re-measured 2026-08-12 after the corridor fix: unchanged, 18/failed
   and 66/failed. The fix gates only the li promotion, which is behind
   a flag, so this number was never going to move -- confirming it did
   not is what says the fix cost nothing here.
2. ~~**`column_metal` does not report a shape that is really there.**~~
   SETTLED 2026-08-12, and the diagnosis was wrong twice over. The
   corridor test failed open in BOTH halves:

   - `pin_layer_corridor_clear` asked `column_blockers(net, col, col,
     ...)` -- a column of ZERO WIDTH. A track is reported only when
     `lo <= t.coord <= hi`, so a zero-width query matches a track only
     when the trunk lands exactly on one, and otherwise reports
     nothing whatever is there. Measured: trunk at 309900, tracks at
     309800 and 312800, "clear".
   - `column_metal` cannot report device metal AT ALL, and never
     could since device geometry became "a pin of nobody": `build()`
     sends it to `Track.block()` (the `pins` dict) and `column_metal`
     reads `Track.wires`. Its docstring still promised the opposite,
     which is what sent two rounds of work at the band width.

   Widening the band changed nothing because the band was never the
   problem -- the half of the test that can see device metal was the
   half being asked a degenerate question.

   Both halves now ask over the same band. Asked properly the same map
   returns 8 `!device` blockers, and klayout confirms them: an li bar
   x 29.54..31.14, y 6.60..7.00 inside `JNWATR_NCH_2C5F0`, straight
   across the trunk column at x 30.84..31.14. So the route was not
   0.05 um from a pin by bad luck -- it was crossing a device rail,
   and the 0.05 um li.3 was the visible corner of that.

   Consequence: `CICPY_LI_LOCAL` now promotes NOTHING across the five
   cells. Its one promotion was illegal. A real candidate needs a
   column with no device rail in it, and the tests that stayed dark
   are the tests that made it look otherwise.
3. ~~**A same-layer leg does not extend onto its pin.**~~ DOES NOT
   REPRODUCE, 2026-08-12. Declared directly -- `('VSS', 'M1', '-|--',
   'trunktab')` in LELOTEMP_OTAR's n_load_a -- the cell builds 0 DRC
   and LVS "Circuits match uniquely": `routeOne`/`addHorizontalTo`
   draw the leg from the pin's own `centerX`, and on li it lands. The
   0.05 um gap that this item was written from was the illegal
   geometry of item 2, read as a leg that stopped short.

   What is NOT proven is the LI_LOCAL swap path, which takes a route
   planned for M2 -- trunk column, cut options and all -- and changes
   the layer late. That is a different path from a route declared on
   li, and it has no clean candidate to run on until item 2's
   consequence is dealt with.
4. **LELOTEMP_BIAS_IBP: 8 DRC -> 3**, 2026-08-12. The layer was the
   CUT layers, not li: the parent and a subcell each contacting the
   same port and landing tens of nanometres apart, which magic cannot
   represent as one tile. `_alignCutsToSubcellCuts` snaps them
   together. LELO_TEMP fell 95 -> 90 with it. The remaining 3 are all
   one site and one cause -- a subcell's via that the parent's
   collection never sees. Characterised at the end of this file.
5. **LELO_TEMP's 90 DRC** -- 778 lines of hand-drawn `wire()`/`stk()`
   with literal offsets. A conversion, not a bug fix. Scope it first.
6. **Three `beforeRoute` hooks left**: p_bias (VBP is a corner on M4),
   p_sw (claims its whole subcell), n_mirr (retyped to Stack its VD3
   splits cleanly and DRC stays 0, but VCP is left open).

## Two process rules this cost real time to learn

- **CHECK THE BUILD EXIT STATUS.** `make drc` reads whatever is on
  disk. A crashed `make mag` leaves half the subcells from this run
  beside half from the last, and every downstream number is then a
  measurement of nothing. This happened twice in one night and
  produced a confident, wrong claim both times.
- **Look at geometry, not logs.** Every question that stalled on log
  reading -- which layer, which cells, what is 0.05 um away -- was
  answered in one klayout probe listing shapes and their cells.
- **A test that says "clear" has to be shown answering "not clear".**
  Both halves of the li corridor test were structurally incapable of
  refusing anything, for two different reasons, and both read as a
  clean pass for weeks. The probe that settled it did not ask "why did
  this fail" -- it asked the SAME map the same question over four
  bands and printed what it holds, and the degenerate one stood out at
  once. Ask a predicate for its evidence, not its verdict.

---

# AI additions to plan

## Context

The plan asks for one pass, and for a `top.py` an AI writes and a human reads:
no custom route code, no stored coordinates, no 1x1 cuts, without losing speed.
Exploring for it turned up two facts that reorganise the work.

### 1. The router already finds a polyline, then throws it away

The maze search produces a path of `(x, y, layer)` nodes. `route_spec`
(`core/mazerouter.py:884-902`) squashes it into one of route.py's eleven canned
shapes plus an absolute `trunkx`:

> *"The search decides WHERE a net should go; route.py knows how to DRAW it...
> **Returns None when the path is not a shape route.py can express** — a
> staircase across several layers has no route type — and the caller should then
> leave the net alone."*

The shapes are `-|--`, `--|-`, `-`, `-|`, `|-`, `--|`, `|--`, `->`, `||`, `-|-`,
`>-|--` (`core/route.py:174-215`). Every one is a two- or three-segment
polyline. When the path is none of them the net is **abandoned** — which is what
the `blocked` entries in the design files are:

    ('PWRUP_1V8', 'blocked', "path ... is not a shape route.py can draw
                              (47 nodes, layers ['M1','M2','M3'])")

and those are the nets `LELOTEMP_OTAR.p_bias` hand-routes in `beforeRoute` —
the custom route code rule 1 wants gone.

**A route is a story: a list of anchored steps, spelled `~`.** It is the native
form of what the search produces, so nothing is squashed and nothing abandoned
(**rule 1**, by deleting hooks rather than adding API); a step is an anchor plus
an offset in grid units from the tech, never nanometres (**rule 3**); it reads
top-to-bottom as what the wire does (**the Goal**); and a declared story
replays without searching, keeping the speed the `wires` blocks bought.

`~` is added *beside* the eleven existing shapes, so nothing that works today
can break.

### 2. The technology-independent anchor already exists

`channelTrackCoord` (`core/layoutcell.py:2766-2784`):

> *"Tracks are counted from the low edge at the ROUTE pitch for the channel's
> direction, so **the same index means the same relative position whatever the
> technology makes the pitch**."*

`addRoutingChannel` → `channelTrackCoord` → `_resolveChannelOptions`
(`:2732`, `:2766`, `:2786`) already turn `vchannel=bias,vtrack=2` into a
coordinate at route time, and `SidecarPycell.afterPlace` **already registers a
vertical channel per subcell** (`core/sidecarcell.py:165-167`). So a design can
already write a technology-independent trunk today. The maze router just never
emits one — it emits the resolved `trunkx` instead.

That makes rule 3 the cheapest part of this, not the most expensive: the
polyline's waypoint vocabulary is `channel + track index` (exists), a pin or
instance terminal rect, and a grid offset. Almost nothing new.

cicpy already wrote the rule down, and `wires` broke it — `route.py:1056-1059`:

> *"bandy and trunkx are absolute coordinates and exist only as the resolved
> form of hchannel/vchannel, which is what a pycell writes. **Do not put them in
> a design**: a coordinate survives neither a resize nor another technology."*

### 3. Two blockers I flagged earlier are smaller than they looked

- `MagicDesign.getLayoutCell` (`eda/magicdesign.py:91-95`) consults only
  `maglib`. `addInstance` (`core/layoutcell.py:122-160`) wants only `.name`,
  `.libpath` and `libshift`, and already defaults `libshift` to `(0,0)` (:151).
- **Origin normalisation is not needed.** It exists only because
  `write_stack_cells` builds subcells from *the parent's own `Instance` objects
  at the parent's coordinates* (`core/subcell.py:619-622`). A subcell built from
  its own `Subckt` is placed from the origin like any other cell.
- And **`CellGroup` is already a `LayoutCell`** (`core/cellgroup.py:213`,
  `StackGroup(CellGroup)` at `:565`) — so `class pmos(Stack or other
  LayoutCell)` is already literally true, and all 20 existing subcell hooks
  already scope themselves to their own members with `includeInstances`.
  Narrowing `self.layout` from the parent to the subcell's own cell is a
  semantic no-op for every one of them.

## Stage 0 — free wins and the fingerprint fix

Cheap, independent, and the fingerprint one is what stops this project throwing
away the measured replay speedups (74s→0.5s BIAS_IBP, 15s→0.5s OTAR).

- **`stack_key` becomes translation-invariant.** `core/routeplan.py:44-51`
  hashes absolute `int(i.x1), int(i.y1)`; subtract `min(x1)`/`min(y1)` over the
  members first. Then re-basing every subcell to its own origin in Stage 4 does
  **not** invalidate a single `wires` block. Without this, every block has to be
  regenerated by hand.
- **Fix a real bug:** `routeplan.py:95-96` sizes a replayed wire's landing claim
  with `Cut.getInstance(pin_layer, layer, 1, 1)` while the route draws a 2x1, so
  replayed claims under-reserve today.
- **Delete `placed_at`** (`core/subcell.py:822`) — written, never read.
- Snapshot harness for all `.mag`/`.cic`/`.sch`/`.sym` + DRC counts + LVS
  verdicts across the five prototype cells.

**Gate:** byte-identical.

## Stage 1 — prove the polyline before building it

Half a day, no production code, and it decides every signature after it.

Take every `trunkx=` and every `blocked` entry in `LELOTEMP_OTAR.py` and
`LELOTEMP_BIAS_IBP.py` (~15 and ~8) and hand-write each as a `~` story against
the real placement — on paper, before the step types are fixed. Answer with
evidence:

1. What is each trunk x relative to — a pin edge, a tab lane, an instance
   terminal, or a `vchannel` track index that already exists?
2. Do `Start / Move / Trunk / End` plus anchor arithmetic express all of them,
   including the 47-node `PWRUP_1V8` staircase? Which steps are missing?

The residue is the specification for the step vocabulary and for any new anchor.
Writing the stories by hand first is what stops the step types being invented
around the easy cases.

**Two of the hard cases are already done, and they needed nothing new.** Read
off the published `LELOTEMP_OTAR_P_BIAS`:

- `PWRUP_1V8`, refused as "47 nodes", is **one vertical M2 rail** on the two
  rightmost of 18 tracks (`t16 @233600`, `t17 @236600`, y 491000..611000) —
  `Trunk("v", at=TabLane())`, one step.
- `VBP`, refused as "15 nodes", is a **three-segment Z on M4**: bottom leg
  t6→t16 at y 449000, riser at t4/t5, top leg t5→t1 at y 565000. That is
  already the `-|--` shape.

The node counts are an artefact of the search stepping off the pin layer and
back — `route_spec`'s own comment: *"a path bends for its own reasons... and
reads as a bend even when the pins are squarely in line."* **47 nodes is not 47
corners.** So the risk is not that the step vocabulary is too small; it is that
the emitter gives up too early. Budget accordingly: less design, more emitter.

### MEASURED (2026-08-11): `CICPY_TRUNK_REPORT=1 make mag`

`Route.trunkAnchors()` resolves every pin anchor and reports which one
reproduces a route's trunk. Over both hierarchical designs, **19 resolved
trunks**:

| | count | verdict |
|---|---|---|
| exactly a pin anchor, `off=0` | **10** | `trunktab` ×4, `trunkright` ×3, `trunkleft` ×3 |
| within 1000 of `trunktab` | **7** | R1<0..4> ×6, VDD_1V8 ×1 |
| an L-route's vertical leg | **2** | `-|--` on M2, 4100 left of `trunkright` |

The 7 near-misses are all *left* of the tab centre by 800–1000 — under half a
wire width, and all of one sign. That is the search snapping to its own
TrackMap grid, whose origin is `min(pin.x1) - margin`
(`mazerouter.py:1303-1306`) rather than anything in the design.
**Unifying that grid with `channelTrackCoord`'s converts all 7 to exact
anchors**, which is the single highest-value change in the whole emitter.

Only **2 of 19** genuinely lack vocabulary, and both are `-|--` L-routes where
"one trunk coordinate" was the wrong model to begin with — an L has a corner,
not a trunk. That is precisely what a polyline expresses and a single anchor
cannot.

### And the 18 `blocked` entries

| reason | count | does the polyline fix it? |
|---|---|---|
| `no path ... closest approach N away` | 8 | **No** — and it does not need to: all 8 are VDD_1V8/VSS, which the ring and strap machinery connects at cell level. The designs pass LVS with these blocked. |
| `not a shape route.py can draw` | 5 | **Yes**, directly |
| `pins share only -N of column, a straight vertical cannot land` | 3 | **Yes** — the pins do not overlap in x, so no `\|\|` can work; an L or Z can |
| `trunk N lies outside the pins' common overlap` | 2 | **Yes** — an anchor problem, not a path problem |

**10 of 18 blocked nets are polyline-fixable, and the other 8 were never the
stack router's job.** Together with the trunk table: the vocabulary is not the
risk. The emitter is.

## Stage 2 — `~`, a twelfth shape: the route story

**Additive, not a replacement.** `routeType` is passed through untouched
(`addConnectivityRoute` `core/layoutcell.py:2667` → `Route.route_`
`core/route.py:23`), so `~` slots into the dispatch at `route.py:174-215` as one
more `elif`. The existing eleven are not touched, not re-expressed, and cannot
regress. Re-expressing them as `~` later is optional cleanup, never a
prerequisite.

`routeType` accepts a `Path` object as well as a string — no new parameter
anywhere in the call chain — and `~` is its textual shorthand.

### `Path` subclasses `Route`

Not merely tidy — it is what makes the path get *drawn*. `isType` walks the MRO
(`core/rect.py:373-381`), so a `Route` subclass answers `isRoute()` True, and
two existing mechanisms depend on that:

- `LayoutCell.route()` iterates `for r in self.routes: if r.isRoute():
  r.route()` (`core/layoutcell.py:2503`). An object that is not a `Route` is
  silently **skipped** — built, added to the cell, never drawn. That is the
  same class of failure the codebase has been bitten by before ("it logged a
  success and left every net it touched open").
- `_attributeInstanceBody` walks a rect's parents for `isRoute()` to decide a
  via cut belongs to the route's net (`core/layoutcell.py:800-812`). Without it
  a path's own via enclosures come out unattributed, are marked
  `device_metal`, and become hard obstacles that block the path from itself.

`Path.__init__` therefore calls `Route.__init__(net, layer, start, stop,
options, "~")` and only then records its steps, so the whole option machinery —
cut counts, `startLayer`/`stopLayer`, trims, keepouts, `routeWidth` — applies
unchanged, and `Path` has the same interface as `Route` by construction.
`route()` is the one override: walk the steps instead of dispatching on
`self.routeType`. `_annotateRoute` debug metadata, `route_owner_info` and
`cicpy checkroutes` then work on paths for free.

Needs a `toJson`/`fromJson` pair so a path round-trips through the `.cic`, which
`Route` does not currently provide for its own shape either — check before
assuming it is free.

### What a story is actually for: ACCESS

The channels already solve the trunk — `addRoutingChannel` registers them and
`SidecarPycell.afterPlace` makes one per subcell. What is unsolved is **getting
into and out of a channel**: pin → up → across → into the lane → ride → out →
down → pin. So the common story is short and stereotyped, and the step
vocabulary should make the access explicit rather than the trunk.

### The story, in steps

**Steps are methods on a path object, never module-level names.** `Start`,
`Move`, `End`, `Track`, `Pin` are exactly the words a design file would collide
with — it already imports `SidecarCell, Stack, Mirror` and defines its own
nested classes. One object, one import, no namespace to pollute:

    def beforeRoute(self):
        p = self.path("VBP", "M1")          # knows its net and start layer
        p.start()                           # all matched start rects
        p.up()                              # via to the next layer up
        p.move(p.pin("xba7", "D") + p.PITCH)
        p.trunk("v", at=p.tab_lane())
        p.move(p.pin("xba6", "D") + p.PITCH)
        p.down()
        p.end()                             # connect to the stop rects

Each call appends a step and returns `p`, so chaining also works — but the
one-call-per-line form is what should be written and generated. The router
regenerates these, and a step per line diffs as one changed line, where a single
chained expression diffs as the whole route.

The anchors and the units hang off the same object — `p.pin(...)`,
`p.port(...)`, `p.track(ch, i)`, `p.tab_lane()`, `p.right_of_pins()`, `p.PITCH`,
`p.SPACE` — so the design file's only new name is `p`. (Lowercase methods per
Python convention; the casing is cosmetic and yours to pick.)

`p.up()` / `p.down()` step one layer along the technology's own chain — the
`next` / `previous` links `_layersDirectlyConnect` (`core/layoutcell.py:543`)
already walks — so a story never names `metal3`. `p.up("M4")` names a target
when a story genuinely means "get to the thick metal". A via is placed wherever
a step changes layer, sized by `_fittedCut`.

**Serialised form for generated blocks.** The router writes tuples, which the
path replays identically:

    wires = [("VBP", "M1", "~", [("start",), ("up",),
                                 ("move", "xba7:D", "+1PITCH"),
                                 ("trunk", "v", "tab_lane"), ("down",),
                                 ("end",)])]

Same steps, same validation; the builder is for hands, the tuples for the
emitter.

### The vocabulary must be open

We will not get the step types right first time, so the design must not require
it. Each step is a small class with one method — "given the run so far, extend
it" — registered by name, so a new construct is a new class beside the others
and touches nothing central. Same for anchors. Concretely: no `if step_type ==`
chain anywhere, no closed enum, and the drawing loop knows only the interface.
A design or a future stage can then add `Jog`, `Comb`, `Bus` without a
migration, and an unknown step name fails loudly at parse time rather than
drawing something plausible.

### Anchors and offsets

**Pin-derived first, track index only as a fallback, never a coordinate.**
A pin anchor names *why* the wire is where it is — the tab lane, the pins' right
edge — so it reads as intent and survives the column gaining a track. A bare
index does neither. This is also what the design already says by hand for both
of the hard nets.

    TabLane()  RightOfPins()  LeftOfPins()     # preferred: the pins ARE the spec
    Track(channel, index)                      # fallback, reusing channelTrackCoord
    Pin(inst, terminal)   Port(name)           # a point to move to

**Offsets come from the METAL rules, not from the routing grid.** Two units,
both per-layer and both read from the `.tech`:

    SPACE      the minimum edge-to-edge gap                  = space
    PITCH      one lane over, centre to centre               = width + space

So `Pin("xba7","D") + 1*PITCH` is "one legal lane right of that pin" and is
correct by construction in any technology. `SPACE` is the right unit when
clearing a pin edge; `PITCH` when stepping to the next lane. Ordinary Python
operator overloading (`__rmul__` on the unit, `__add__` on the anchor) — no
metaclasses, no magic.

This is the ruler the framework already uses where it gets it right:
`clearance()` is `width + space` (`core/mazerouter.py:190`), `via_is_free`'s
margin is `space + width//2` (`:328-329`), `_resolveTrunkAlign` offsets by
`w//2` (`core/route.py:530-534`). It is also what BIAS_IBP's typed `2400`
approximates — that constant is `space + width/2` under another name, and once
the unit exists the literal has nowhere to hide.

`ROUTE.horizontalgrid` / `verticalgrid` survive only as *channel track indices*,
never as an offset unit — and per the stage below they should become `PITCH`
too. Never a nanometre, which is rule 3 enforced by the type rather than review.

`TabLane` / `RightOfPins` / `LeftOfPins` are `trunktab` / `trunkright` /
`trunkleft`, which `_resolveTrunkAlign` (`core/route.py:497-537`) already
implements. The step vocabulary is naming what exists, not inventing.

### Drawing

- **Through route.py, not around it.** Widths, via enclosures, cut placement and
  alignment are per-segment machinery that already works; `route_spec`'s
  docstring records what happened when it was bypassed — *"272 DRC errors of
  minimum width, minimum area and via enclosure."*
- Vias where consecutive steps change layer; `_fittedCut`
  (`core/layoutcell.py:1981-1995`) already picks the largest fitting array,
  which satisfies rule 2 for free.
- A named, reusable story can be a `Path` subclass — that is the "propose new
  route.py functions, or classes" escape hatch, and it is where a recurring
  idiom like the gate-tab lane should end up.

**Gate:** the five cells are byte-identical *by construction* (nothing they use
has changed), plus a new unit test per step type asserting a hand-written `~`
draws exactly what it says. First real user is Stage 3.

## Stage 3 — the router tells the story

- `route_spec` (`mazerouter.py:884`) stops squashing its path into one of the
  eleven and stops returning `None`: it emits a `~` story. The `trunkx=`
  emitters (`:992, 1004, 1069, 1087, 1414-1418, 1467`) go with it. A path that
  *does* fit a canned shape may keep emitting that shape — it reads better, and
  `~` is only needed where the shape vocabulary ran out.
- **Round-trip test, automated:** search → emit the story → replay → assert
  identical rects. A half-pitch drift is a short, not a warning, so this is a
  test and never a comparison by eye.
- **Resolution order, first that round-trips wins:** `TabLane` /
  `RightOfPins` / `LeftOfPins` — recompute each from the net's own rects with
  `_resolveTrunkAlign`'s arithmetic and compare — then a channel track index,
  then blocked. Pin-derived beats grid-derived because it survives a pitch
  change and says why.
- A path that cannot be anchored reports blocked *with a reason naming the
  failure* ("trunk 273300 is 1400 off the nearest bias track; no pin anchor
  matches"), never falls back to a coordinate. Those reasons are the spec for
  the next anchor form.
- `Route.__init__` gains a guard: `trunkx`/`bandy` in the options without an
  internal resolver having set it is an ERROR naming the caller. Plus a CI lint
  rejecting `=\d` in route option strings and bare integers ≥1000 in
  `design/**/*.py` — that catches `trunkx=304100` and BIAS_IBP's
  `2400/2500/5000/20000` with one rule.
- Regenerate the `wires` blocks. Previously-blocked nets now route, so the
  `beforeRoute` hooks in `p_bias`, `p_sw`, `n_load_a`, `n_load_b`, `n_mirr`
  should be deletable — **delete them and check DRC/LVS holds.**

**Gate:** DRC/LVS parity. Geometry is *expected* to change where a net was
hand-routed; each change gets looked at.

### Stage 3, the emitter half — DONE (2026-08-12)

`trunkAnchorCoords` is module level and shared, so the router can ask
the inverse question -- given the lane the search chose, which anchor
would have produced it -- and write the anchor. And the search was
MISSING them for the reason Stage 1 predicted: its TrackMap grid is
originned at `min(pin.x1) - margin`, so every miss was 800 or 1000 to the
LEFT of `trunktab`, all of one sign. Inside half a wire width the two are
the same lane and the pins win.

The payoff is bigger than the tidiness. Fresh search, no wires blocks:
**OTAR 128 DRC -> 0, BIAS_IBP 182 -> 8** -- the hand-tuned quality,
found by preferring the pins over the grid.

Design side: **all 19 coordinates gone**, DRC/LVS/cost identical. Ten
were exactly an anchor; the rest the same lane within half a wire. A
coordinate that reaches a sidecar anyway is reported at compile.

The round-trip test is in (`tests/unittests/test_trunk_anchor.py`): the
anchor the router writes is the anchor route.py reads, asserted through
both code paths, with the exact-match rule pinned so a near miss can
never silently move a wire.

**CORRECTED 2026-08-12: THE CONNECTIVITY GAP IS *NOT* CLOSED.** The
fresh-search numbers below were read off a build that had CRASHED
partway through the cell -- `_preferPinAnchor` returned a bare int
where a (lane, lo, hi) tuple was expected, it went into `claimed`, and
the next net to search unpacked it. Only a fresh search hits it, since
a replayed wire never searches, and `make drc` happily read the
half-new, half-stale files left behind. With the crash fixed and the
build completing: **OTAR 18 DRC / failed pin matching, BIAS_IBP 66 /
failed**. The declared-wires build was never affected and is still
0/0/0/8/95, every cell matching.

The pad guard below is still right and still worth having -- a width
test refuses every gate tab in this technology -- but it did not close
the gap, and the claim that it did was measurement error. The lesson
is cheap and was learned twice in one night: CHECK THE BUILD EXIT
STATUS. `make drc` reads whatever is on disk.

**(superseded) THE CONNECTIVITY GAP IS CLOSED (2026-08-12).** The stack router
refused any via whose pad is wider than the narrowest pin it lands on,
and the smallest li-to-metal pad here is 4000 against a 3200 gate tab
-- so it refused every gate tab there is, and those nets were simply
left open. What overhanging costs is SPACE, which `via_is_free` already
answers at the candidate's own size; and the router must state WHICH
pad it checked, because asking at the single-cut size while route.py
draws its 2x1 default validates one via and draws another (71 DRC
errors, measured). Fresh search, no declared wires at all:

    OTAR      0 DRC, Circuits match uniquely   (was 0 DRC, LVS FAILED)
    BIAS_IBP  8 DRC, Circuits match uniquely   (was 8 DRC, LVS FAILED)

Both identical to the hand-tuned blocks. **The router now reaches the
same answer unattended as the design reaches by hand** -- asked for
PWRUP_1V8 it emits ('PWRUP_1V8', 'M2', '||', 'trunktab'), which is what
the hook beside it says in longhand. That is the plan's Goal, on these
two cells.

**The hooks are NOT deletable yet, measured.** Stage 3's last bullet
says the `beforeRoute` hooks in p_bias / p_sw / n_load_a / n_load_b /
n_mirr should come out once the previously-blocked nets route. Tried,
one subcell at a time, each with its `blocked` entries removed so the
router had to search:

| hook removed | DRC before the pad fix | after |
|---|---|---|
| n_load_b (VD2) | 0 -> 6 | 0 -> **4**, LVS still matches |
| p_bias (VBP, PWRUP_1V8) | 0 -> 28, LVS fails | PWRUP_1V8 now the router's |

**What the last hooks are actually for is now known**, and it is one
missing capability rather than general quality. n_load_b's VD2 mixes
two pin SHAPES -- wide drain bars and narrow gate tabs -- and the
design says so in its own comment: "no single vertical lands on all of
them, so two do". The router draws one rail and collides; the hook
draws two, scoped by instance regex, and is clean. Same for n_load_a,
n_mirr and p_cas.

**SHIPPED (2026-08-12).** `lanes_over_pins` is the minimum piercing of
the pins' legal intervals -- greedy, which is optimal on intervals --
and a pin wide enough for two lanes lands in both groups, which is the
join. Three things separate "connected" from "clean", each measured:
the rails go on the pins' own layer (M2 instead: 52 DRC and a failed
pin match), each rail takes its GROUP'S anchor rather than the greedy's
lane (arbitrary lanes: 80 DRC), and a group holding narrow rects wants
trunktab where a group of bars wants trunkright.

Asked to route n_load_b it emits the hook beside it verbatim, both
scopes included. **n_load_a and n_load_b now have no beforeRoute at
all** and LELOTEMP_OTAR is still 0 DRC / matches uniquely.

Left: p_bias (VBP on M4, a corner rather than a rail), p_sw (claims its
whole subcell) and n_mirr. n_mirr is the closest -- retyped from Mirror
to Stack its VD3 splits cleanly and DRC stays 0, but VCP is left open
and LVS fails, so it wants one more capability, not this one.

## Stage 3b — a channel track is one legal lane

Independent, small, and it removes a workaround from every design file.

`channelTrackCoord` (`core/layoutcell.py:2766-2784`) spaces tracks by
`ROUTE.horizontalgrid` (30) or `verticalgrid` (40). Every metal M1..M5 is
`width 30, space 30`, so **the legal pitch is 60**. Channel tracks are therefore
half a lane apart, and track *N* and *N+1* abut and short. The router already
knows — `clearance()` (`core/mazerouter.py:178-192`): *"THE TRACK GRID IS FINER
THAN THAT... Two nets on ADJACENT tracks abut exactly and short."*

The designs have been hand-compensating. Every `track:` in `LELOTEMP_OTAR.py`
and `LELOTEMP_BIAS_IBP.py` is **even** — 0, 2, 4, 6, 8, 10, 12, 14, 16 — with
the comment "channel tracks two apart so the drops' via pads clear the
neighbouring bars". On a horizontal channel it is worse: pitch 40 against a
legal 60 means "two apart" is 80 and wastes 20 of every lane.

Change the channel pitch to `width + space` for the channel's layer. Then
consecutive indices are consecutive legal lanes, the designs renumber
`0,2,4,...` → `0,1,2,...`, and the "two apart" rule disappears from the
comments because it disappears from the arithmetic.

**Not geometry-preserving** — old track `2j` sat at `lo+(2j+0.5)*30`, new track
`j` at `lo+(j+0.5)*60`, half a width apart — so this is a deliberate
re-baseline with its own DRC/LVS gate, not a refactor. Do it before Stage 5, so
the hierarchy change is not competing with a track renumber.

## Stage 4 — the resolution seam

`MagicDesign.getLayoutCell`: `self.cells` first, `maglib` second. This ordering
is load-bearing, not cosmetic — `scanLibraryPath` globs `libdir**/*.mag`, which
on a rebuild includes the *previous run's* subcell files, so preferring `maglib`
would silently build the parent against last run's subcells.

## Stage 5 — the hierarchy, in memory

- **Where: `LayoutCell.layout()`**, a no-op `self.hierarchy()` overridden on
  `HierCell`, called at `core/layoutcell.py:3013` before `beforePlace`. *Not*
  `readFromSpice` — `dirname`, `place_gbreak`/`place_xspace`/`place_yspace` and
  `_ensure_default_pycell` are all set **after** the read (`cic.py:485-505`), so
  a subcell built there inherits none of them and cannot find its own pycell.
  `layout()` is one line later and has everything, and it is the seam the team
  already chose for `_runStackPycells`. Classic pycells get a no-op, so
  `cic.py` needs no change for the hierarchy at all.
- **Split from the bare netlist:** membership by `instRegex` over
  `ckt.instances`; ports by the rule already proven in `plan_subcells`
  (`core/subcell.py:319-323`). Write `Subckt.splitByMembership` rather than
  reusing `makeInstGroupSubckt` (`cicspi/subckt.py:95-117`), which has four
  defects: `startswith` not regex, all-member-nodes not the boundary set, a
  stale `inst_index` after `instances.remove`, and `SubcktInstance.fromSubckt`
  aliasing `self.nodes = sub.nodes`.
- **Build order:** each subcell placed, routed and written as its own cell,
  registered in `design.cells` ahead of the parent, then the top is placed.
- **Fills are placement-time** (`core/cellgroup.py:1408-1440`), so each
  subcell's netlist is amended after its own placement. Safe because every fill
  terminal rides the subcell's own supply, which is already a port — so a fill
  cannot change the port set the pre-placement split computed. Assert that.

**Deleted:** `<CELL>_HIER.spice`, `sch2subcells`, `--outcell`, `--hier`,
`_declares_hier`, `_hierarchify`, `cic_subckt`, `write_stack_cells`,
`HierLayoutCell`, and the `hier`/`assembled` role split added earlier today.
`HierLayoutCell.place`'s row-tiling body moves to the top's `afterPlace`.
**Kept:** `cic_fingerprint` (the grouping-drift guard), `SidecarPycell` (now the
recipe for the top *and* each subcell), and the `<SUBCELL>.py` file escape hatch
that `LELOTEMP_CMP_P_DIFF.py` and friends use.

**Gate:** DRC/LVS parity — *not* byte-identical, since subcells are now placed
from their own origin. CMP, CCMP and LELO_TEMP must stay byte-identical, since
`hierarchy()` is a no-op for them.

### DONE (2026-08-11). Result, against the stage3 baseline:

| | DRC | LVS | `cicpy cost` |
|---|---|---|---|
| CMP | 0 = | match = | 1554.60 = |
| CCMP | 0 = | match = | 178.20 = |
| OTAR | 0 = | match = | **492.40** (was 500.40) |
| BIAS_IBP | 8 = | match = | **758.22** (was 825.02) |
| LELO_TEMP | 95 = | (VR1 artefact) = | 2322.29 = |

Everything at or better than baseline, and the two hierarchical cells cost
less wire than the two-pass build did. One command, one process: `make
subcells hier` and `<CELL>_HIER.spice` are gone.

**What the plan got right.** The seam (`layout()`, not `readFromSpice`), the
in-memory split, `design.cells` before `maglib`, and the role split being
derivable rather than passed in — `SidecarCell()` takes no arguments now, and
what a cell is MADE OF is read off its own `routes` declaration.

**Five things it did not predict**, each measured:

1. **A subcell is tiled by its COLUMN, not by its geometry.** The cell box
   after `layout()` is everything drawn; the box the flat recipe abutted is
   the built `StackGroup`, which can start 4800 inside it (the guard the
   column carries past its own edge so two abutted columns MERGE their
   guards). Tiled by the geometry every seam opened by that much and the
   guards stopped merging: 181 DRC. `HierPycell._setAbutmentBox` translates
   the cell so the column box is at the origin and then STATES the box.
2. **The fills stop existing.** `fillDummyTransistors` pads each column to the
   tallest in its GROUP, and a subcell's group holds one column — so
   `xfill_p_in_a_0` and two others simply were not built, and the schematic
   has them. The netlist is the answer: it NAMES its fills, so
   `fillDummyTransistors(counts=...)` fills to the declared count and height
   matching is only the fallback. After this every subcell is a PURE
   TRANSLATION of its flat placement — verified instance by instance, 20 of
   20 subcells across both cells.
3. **`trunkx` is absolute and `stack_key` is deliberately not.** Stage 0 made
   the fingerprint translation-invariant, which is right for "the same devices
   in the same arrangement" and blind to a block whose coordinates were
   resolved in another frame. Three BIAS_IBP blocks were ALREADY stale that
   way and replaying silently — `p_src` declared a VDD trunk 394400 into a
   column 80000 wide. `wires_lookup` now checks each trunk against the stack's
   own span and searches that net afresh, loudly, instead.
4. **Port position is a floorplan question, and the floorplan is declared.**
   `addAllPorts` takes the first rect on the net; the copy-out publication
   took the pin nearest the centroid of the net's pins OUTSIDE the subcell.
   That centroid is not available before placement, but `rows` is: the net's
   other owners give a direction (`_portDirections`), and the port is the pin
   at that end of the column. Without it VD1's port in `n_load_a` moved to the
   far end of the column and the parent's drop ran the whole column to reach
   it. Supplies keep their own rule — the bulk column, ground low, power high
   — which is intrinsic and needs no direction.
5. **A latent `Path` bug the copy had been hiding.** `Path.route` started its
   cursor at `(0, 0)`, so a story opening with `trunk` drew a leg from the
   COORDINATE ORIGIN to the trunk. Copied out of a parent, that leg started
   outside the copied window and was silently left behind; built from its own
   origin it lands inside the cell. The cursor is `None` until a step sets it.

## Stage 3b — DONE (2026-08-11)

`channelTrackCoord` spaces tracks by `width + space` for the layer named,
or the widest lane in the stack when the caller does not know one, so an
index is legal for whatever rides it. Both designs renumbered
`0,2,4,...` -> `0,1,2,...` and the "two apart" rule is gone from the
comments because it is gone from the arithmetic. DRC/LVS parity on all
five cells; BIAS_IBP cost +0.7% (758.22 -> 763.62), everything else flat.

## Stage 6 — the declarative surface

`self.instRegex`, `self.groupName`, `self.addOrder([...])` in `__init__`;
`SidecarCell` → `HierCell` with an alias for one release. `compile()`
(`sidecar.py:259-286`) reads class attributes without instantiating, so this
needs a *declaration instance*: `Stack.__init__(self, layout=None, name=None)`
that only calls `StackGroup.__init__` when bound to a layout. Convert
`LELOTEMP_CMP.py` (a classic pycell today) as the fifth prototype.

### NOT DONE, and two thirds of it should not be (2026-08-11)

- **The `__init__` surface is a step backwards.** Class attributes ARE the
  declaration, and `compile()` reading them without instantiating is the
  property that lets cic.py decide what a cell is before the technology is
  loaded. Moving them into `__init__` trades a file that can be read without
  running it for one that cannot, and buys nothing.
- **`SidecarCell` -> `HierCell` would be a lie after Stage 5.** A sidecar
  cell is not necessarily hierarchical: LELOTEMP_CCMP is a sidecar made of
  devices. What a cell is made of is now a property of its own declaration,
  which is exactly why the name should not claim it.
- **Converting LELOTEMP_CMP is still open**, and it is the stage's real
  content. It is not free: CMP never calls `stack()` (it relies on the
  framework's own placement) and never fills, so the recipe would re-lay it
  and its `track`-numbered routes would need re-tuning. It is also the only
  byte-identical control left among the prototypes for a cell built without
  `hierarchy()`. Worth doing deliberately, with its own gate, not as a
  by-product.

## Stage 7 — 1x2 / 2x1 cuts minimum — DONE (2026-08-11)

Geometry-changing, therefore never debugged alongside Stage 5.

**The finding that mattered: `cuts` was dead.** `addConnectivityRoute` passed
it to `_annotateRoute` and never to `Route`, so all 14 design sites typing a
number were writing comments and route.py's own 2x1 default decided
everything. The designs were migrated to 2 FIRST and the parameter wired
through second, which makes the no-op provable: DRC, LVS and `cicpy cost`
identical on all five cells afterwards.

The framework `cuts=1` defaults are 2; the ring-to-ring cut is `_fittedCut`
instead of a typed 1x1; the maze router's last-resort lone via is gone and
reports the position it could not serve. It never fires on the five cells.
OTAR's `1cuts` is kept and now says so twice -- a 2x1 pad does not fit
beside that guard ring.

- **framework `cuts=1` defaults** — `core/cellgroup.py:258`, `:263`,
  `core/route.py:1009`, `core/layoutcell.py:2711`, `:2824`. These are what
  enforce the rule; most call sites take the default.
- **hard-coded 1x1** — `core/mazerouter.py:272`, `core/layoutcell.py:2228-2230`.
- **`mazerouter.py:608` last-resort `(1,1)`** — drop it and report the net
  blocked instead: silent unreliability becomes a visible failure.
- `LELOTEMP_OTAR.py:132`'s explicit `1cuts` exists because a 2x1 pad does not
  fit beside a guard ring. Widen the lane or accept the delta — do not migrate
  blind. `route.py:33`'s `vcuts = 1` with `cuts = 2` is a 2x1 already; leave it.

## Stage 8 — the last imperative geometry — DONE (2026-08-11)

`LELOTEMP_BIAS_IBP.route()` builds its powerdown pins from `Rect`, `Cut` and
literals. `addPortOnEdge` (`core/layoutcell.py:2880-2936`) is close but requires
the net to be in `self.ports` (it is an *instance* port here). A
`promoteInstancePort(net, instanceRegex, edge, layer)` covers it, with the
off-centre attach rule derived from `Rules.get(layer,'space')` instead of the
typed `2400`.

Shipped as written. `LELOTEMP_BIAS_IBP.route()`'s twenty lines of Rect and Cut
are two calls; 2400 is `space + width/2`, 5000 is the layer's minimum-area pad,
20000 is twice that pad, and the 1x1 via is `_fittedCut`. 8 DRC and "Circuits
match uniquely", both unchanged.

## Verification

- `cd lelo_temp_sky130a/work && make mag gds drc cdl lvs CELL=<c>`; read only the
  LVS `Final result:` line.
- Snapshot/rebuild/diff all 106 `.mag`/`.cic`, ignoring `timestamp`.
- `cd cicpy && make test` — ten integration suites, four unit tests.
- `grep -c trunkx */design/*/*.py` is 0 after Stage 3.
- Baseline: CMP 0/match, CCMP 0/match, OTAR 0/match, BIAS_IBP 8/match,
  LELO_TEMP 95/"Netlists do not match" (known VR1 label artefact).

## Risks, cheapest falsification first

1. **The two-process split exists because of a *measured* failure**
   (`cic.py:341-347`, BIAS_IBP failing pin matching). Prime suspect found:
   `Subckt.circuits` (`cicspi/subckt.py:9,23-24`) is a process-global set to the
   *first* parser ever constructed, and `write_stack_cells` falls back to it
   (`subcell.py:832-835`). In the new design there is only one parse, so it
   disappears — but prove that first. *Half a day:* call `_spi2mag` twice in one
   process for BIAS_IBP and diff against the two-process build; if it
   reproduces, bisect `Subckt.circuits` / `Cut._cuts` / `Rules.instance` by
   resetting each.
2. **The polyline cannot express the hard paths.** Stage 1 exists for this.
3. **Port *positions* change.** `addAllPorts()` picks ports by its own rule;
   `write_stack_cells` uses an outside-centroid rule plus a bulk-rect rule for
   supplies (`subcell.py:745-813`). Port position drives every parent track in
   the `routes:` tables. Expect a delta and **budget a day re-tuning tracks** in
   OTAR and BIAS_IBP. Most likely source of "parity, but slowly".
4. **Subcell origin is not (0,0)** — guard rings overhang the box
   (`subcell.py:658-667`). *Ten minutes:* hand-write a one-subckt spice file,
   run `cicpy spi2mag`, print `x1,y1`.
5. ~~Drawing polylines reproduces the canned shapes only approximately.~~
   **Retired by making `~` additive.** The eleven shapes are untouched, so
   nothing existing can regress; the only question is whether `~` draws new
   paths correctly, which the Stage 2 unit tests answer directly.
6. **Pre-placement port sets differ from post-placement ones.** Assert
   `plan_from_netlist(ckt)` matches `plan_subcells(placed)` modulo fills and
   taps, before anything consumes it. ~30 lines, no build change.
7. **`.sch`/`.sym`** silently emit symbols with no wires when
   `XschemPrinter.cells` is not pre-populated
   (`printer/xschemprinter.py:417-421`). Keep that step.
8. **Name collisions on the file escape hatch** — generated subcells are named
   `<PARENT>_<SUB>` and files with exactly those names exist
   (`LELOTEMP_CMP_P_DIFF.py`). They must stay findable by `import_beside` and
   not be mistaken for sidecars. Build CMP after Stage 5; it is the only cell
   using them.


# The DRC that is left, and what is known about it (2026-08-12)

Asked for: LELOTEMP_BIAS_IBP and LELO_TEMP DRC clean. NOT ACHIEVED.
Both counts are unchanged from the start of this work -- 8 and 95 --
so nothing here made them worse, but nothing made them go away either.
What follows is everything established, so the next attempt starts from
the end of this one rather than the beginning.

## LELOTEMP_BIAS_IBP: 8 errors, one rule

    "This layer can't abut or partially overlap between subcells"

- **All 8 belong to LELOTEMP_BIAS_IBP itself** -- `drc listall count`
  returns `{LELOTEMP_BIAS_IBP 8}`, nothing to its children. Every one of
  its eleven subcells is 0 on its own.
- Two sites, in `.mag` file units (multiply by 50 for cicpy units):
  `1124 11844 1176 11940` (inside p_src, around its LPI pin) and
  `15772 17152 15829 17200` (inside the OTA, around PWRUP_1V8).
- The rule fires 52-56 times for 8 counted errors.

**Ruled out, each by experiment:**

- *Not* a via hanging over a subcell pin. LELOTEMP_OTAR has two cuts
  that partially overlap a subcell pin (`xp_in_a/VIN`, 3400x8800 over
  3200x4000) and is 0 DRC. The containment census is
  OTAR: 14 inside / 8 containing / 2 partial, at 0 errors;
  BIAS_IBP: 27 / 4 / 2, at 8.
- *Not* the top-level cover. Covering the pin exactly, covering the
  union of pin and via, and removing the cover altogether all give 8.
- *Not* the pin being narrower than the smallest via (3200 against
  3800). Growing the pin at the edge to 4800x4800 changed nothing.
- *Not* introduced by the hierarchy work: the same 8 were there at the
  stage3 baseline, before any of it.

**A minimal reproducer exists**, which is the most useful thing here:
adding one line to LELOTEMP_OTAR.afterPorts --

    layout.addPortOnEdge("M3", "PWRUP_1V8", "top", "-|--", "")

-- creates exactly this error inside OTAR (1 error, 6 fires) and takes
BIAS_IBP from 8 to 6. So one `addPortOnEdge` on a gate tab reproduces it
in a cell that is otherwise clean, in about two seconds per build.

**ANSWERED 2026-08-12, and no display was needed.** The layer is the
CUT layers, and the shape is a via. `drc listall why` gives the error
boxes; klayout then lists every shape in each box WITH ITS ORIGINATING
CELL, which is what magic's own `what` refused to do:

    VIA3 [LELOTEMP_BIAS_IBP]  x 61.280..61.480  y 70.060..70.260
    VIA3 [LELOTEMP_OTAR]      x 61.370..61.570  y 70.080..70.280

The parent and the child are both contacting the same port, each
centring on its own copy of it, and landing tens of nanometres apart.
A contact in magic is ONE tile spanning both metals, so two of them
half over each other have no legal form -- hence the wording about
subcells.

**The first hypothesis was wrong and the falsification is the useful
part.** "Contacts overlapping across cells" is not it: a router via
over a device's own CO happens ~100 times in each of LELOTEMP_CMP,
LELOTEMP_CCMP and LELOTEMP_OTAR, all 0 DRC. Only overlaps on the SAME
cut layer track the errors -- 0, 0, 0 against 2 in BIAS_IBP. A pass
built on the loose criterion would have moved a hundred innocent vias
per cell. One klayout sweep over four cells cost a minute and killed
it.

**Fixed** by `LayoutCell._alignCutsToSubcellCuts`, a pass after
`route()`: a cut of this cell that partially overlaps a SAME-LAYER,
SAME-SIZE cut of a subcell, by no more than its own size, is snapped
onto it exactly. Anything else is left alone and logged -- a cut that
would have to move further is not the same contact seen twice.

    BIAS_IBP  8 -> 3      LELO_TEMP  95 -> 90
    CMP/CCMP/OTAR 0, all five LVS unchanged, cost unchanged

Two traps it cost to find, both about how a cut is placed:

- An `InstanceCut` has NO children. The geometry is in the `Cut` cell
  it references, and that cell is CACHED and SHARED, so the shift is
  `instance.x1 - cell.x1`, not `instance.x1`.
- The same applies when collecting a SUBCELL's cuts, and getting it
  wrong there is silent: the vias land somewhere else in the
  collection and the cut that needed alignment is simply never
  offered one.

**Still open: the last 3, all at one site** -- x 15772..15829,
y 17144..17200 in file units, `VIA1 [LELOTEMP_BIAS_IBP]` at
78.905,85.765 against `VIA1 [LELOTEMP_OTAR_P_BIAS]` at 78.945,85.805.
The parent's stack is collected correctly; the P_BIAS via never
appears in the subcell collection at all, while LELOTEMP_OTAR's own
vias one level up do. So the walk stops somewhere between OTAR and its
subcell -- an unresolved cell in `design.cells`, most likely. That is
the next thing to instrument, and it is the whole of the remaining 3.

Worth knowing: klayout on the flattened GDS (`make kdrc`) reports a
DIFFERENT set -- ct.2 x12, psdm.1 x10, ct.1, via2.1a, 24 total -- so
the magic rule and the sign-off deck disagree about this cell, and
which of them the tapeout actually cares about is a question for the
owner.

## LELO_TEMP: 95 errors, and why they are a different job

LELO_TEMP is the one prototype the plan never converted. Its 778 lines
are `_signal_routes` with a local `wire()` painting raw Rects, `stk()`
placing via stacks, and literal offsets (`- 1500`, `- 4250`, `3000`) --
exactly the custom route code rule 1 forbids and the stored coordinates
rule 3 forbids. Its errors are in that hand geometry, in three clusters
(file units): a met4 bus at y 21790-21820 spanning x 6400-11200, a
met3/met4 knot at 19620-19840 x 21990-22200, and a met1/met2 knot at
29850-30550 x 1690-3730 -- plus 56 fires of the BIAS_IBP rule above,
inherited.

Fixing those 95 one at a time is not the work. Converting LELO_TEMP to
the declarative flow is, and it is a stage of its own: an L-shaped
floorplan that `rows` cannot state, four finished blocks rather than
device columns, and a hand-built signal net between them. It should be
scoped before it is started.
