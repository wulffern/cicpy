---
layout: page
title: Keeping the output on grid
---

# Keeping the output on grid

ciccreator stores coordinates as integer ångström. cicpy is Python, so a
coordinate is whatever arithmetic produced it, and nothing in the code
says otherwise. This is the plan for closing that gap.

## What was measured, 2026-08-05

The output is currently clean. Every coordinate in `REYNORES`,
`LELOTEMP_OTAR` and `LELOTEMP_CMP` is an integer multiple of 100 database
units, routes included: gcd of all coordinates is exactly 100, and there
are no non-integer values.

Nothing enforces that. `Rect` stores what it is handed:

- `rect.py:188` `centerX()` returns `x1 + width()/2`, true division
- `rect.py:203` `moveCenter()` does `xc - w/2`
- `__init__`, `moveTo` and `setRect` coerce nothing

It holds today because the inputs happen to be even multiples. The hazard
is countable: **11 rects in REYNORES and 26 in LELOTEMP_CMP have widths
that are not an even number of grid steps**, so `centerX()` on any of
them lands halfway between grid points. Anything that centres on one goes
off grid.

That is not hypothetical. Centring a trunk via on `rect.centerX()` in
`route.py::_instantiate_cut_on_rect_x` produced a `via2.1a` width error,
and the cause was exactly this. See the note in
`rey_atr_sky130a/design/REY_ATR_SKY130A/REYNORES.py`.

## Not Cython

Three reasons, in order of weight:

1. **It does not solve the stated problem.** `cdef int x1` stops floats,
   but an integer can still be off grid: 2350 is a good int and a bad
   coordinate. The invariant is *multiple of grid*, which no type system
   expresses. Typing would have caught none of the via bug above, where
   the wrong answer was already an integer.
2. **It costs the pure Python install.** cicpy is pip installable from
   source. Cython means platform wheels, a build toolchain in CI and in
   the docker images, and a compile step between editing a `.py` and
   running `sch2mag`.
3. **Speed is not the constraint.** `sch2mag` wall clock is dominated by
   the magic and xschem subprocesses.

## The plan

### 1. Assert at the boundary

One check where coordinates leave: `MagicPrinter` and the `.cic` writer.
Every emitted coordinate must satisfy `v % grid == 0`, and the failure
must name the layer, the net and the rect.

Cheap, catches drift whatever produced it, and turns a silent DRC hunt
into a stack trace. Do this first and alone: if it never fires on the
real designs, step 2 is not urgent, and if it does fire the message says
where.

The grid comes from the tech file's `"grid"` value, not a constant. gamma
differs between libraries — 100 in tech_sky130A, 200 in rey_atr — so the
database units per grid step move with it.

### 2. Make Rect integral by construction

Coerce in `__init__`, `moveTo`, `setRect`, `moveCenter`; `//` rather than
`/`. Pure Python, no build change. This is the discipline ciccreator gets
from its integer ångström.

Rounding has to be decided, not defaulted: snapping is a change in
geometry and a rect that snaps outward is not the same rect.

### 3. Decide what centring means on an odd width

The 37 odd-width rects above are real and will not go away. Something
that centres on them needs a defined rounding direction, and picking it
is a semantic decision about the layout rather than a typing one. That is
the strongest argument that this whole question is a design problem: a
type annotation would not have decided it either.

## Where to look

| what | where |
| :--- | :--- |
| Rect coordinates and centres | `src/cicpy/core/rect.py` |
| the via centring that broke | `src/cicpy/core/route.py::_instantiate_cut_on_rect_x` |
| output boundary | `src/cicpy/printer/magicprinter.py` |
| grid value | tech file, `"grid"`, scaled by `"gamma"` |
