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

STILL OPEN from Stage 3: the 10 polyline-fixable `blocked` entries, the
`beforeRoute` hooks in p_bias / p_sw / n_load_a / n_load_b / n_mirr that
rule 1 wants gone, and the round-trip test (search -> emit -> replay ->
assert identical rects). The fresh-search LVS still fails where the
declared blocks pass, which is the next thing to look at: the DRC gap
closed, the connectivity gap did not.

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
