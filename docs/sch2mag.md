# sch2mag

`sch2mag` is the schematic-to-layout entrypoint. It netlists the schematic, builds the connectivity graph, runs placement and routing, and writes both Magic and `.cic` layout output.

This fixture stays standalone for CI. The test driver clones the required repositories, then runs the local `work/` flow inside `lelo_temp_sky130a`.

```bash
make test && printf 'Generated files:\n' && ls -1 lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.mag
```

```bash
cd lelo_temp_sky130a && git reset --hard
HEAD is now at d85fba8 Updated images
cd lelo_temp_sky130a/work && cicpy sch2mag LELO_TEMP_SKY130A LELOTEMP_CMP
xschem -q -x -b -s -n ../design/LELO_TEMP_SKY130A/LELOTEMP_CMP.sch -l xsch/xsch_LELOTEMP_CMP.log
cp xsch/LELOTEMP_CMP.spice xsch/LELOTEMP_CMP.spice.bak
cat xsch/LELOTEMP_CMP.spice.bak | perl ../tech/script/fixsubckt > xsch/LELOTEMP_CMP.spice
rm xsch/LELOTEMP_CMP.spice.bak
Adding cut cut_M1M2_2x2
Adding cut cut_M1M2_1x2
Adding cut cut_M1M2_2x1
Adding cut cut_M2M3_2x1
Adding cut cut_M2M3_1x2
Adding cut cut_M3M4_1x2
Adding cut cut_M2M4_2x1
Adding cut cut_M3M4_2x1
Adding cut cut_M2M4_1x2
Generated files:
lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic
lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.mag

```


Command under test:

```bash
cd lelo_temp_sky130a/work
cicpy sch2mag LELO_TEMP_SKY130A LELOTEMP_CMP
```

Standalone test driver:

Makefile:
```makefile
PYTHON ?= python3

lelo_temp_sky130a:
	git clone https://github.com/wulffern/lelo_temp_sky130a lelo_temp_sky130a
	git clone https://github.com/analogicus/jnw_tr_sky130a jnw_tr_sky130a
	git clone https://github.com/wulffern/lelo_atr_sky130a lelo_atr_sky130a
	git clone https://github.com/analogicus/jnw_atr_sky130a jnw_atr_sky130a
	git clone https://github.com/wulffern/tech_sky130A tech_sky130A

test: lelo_temp_sky130a
	cd lelo_temp_sky130a && git reset --hard
	cd lelo_temp_sky130a/work && cicpy sch2mag LELO_TEMP_SKY130A LELOTEMP_CMP
	@test -f lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic
	@test -f lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.mag

svg: lelo_temp_sky130a
	cicpy svg lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic \
		lelo_temp_sky130a/tech/cic/sky130A.tech LELOTEMP_CMP \
		--I jnw_atr_sky130a/design/JNW_ATR_SKY130A.cic \
		--I jnw_tr_sky130a/design/JNW_TR_SKY130A.cic

clean:
	rm -rf lelo_temp_sky130a
	rm -rf jnw_tr_sky130a
	rm -rf jnw_atr_sky130a
	rm -rf tech_sky130A
	-rm -rf LELOTEMP_CMP_svg LELOTEMP_CMP_svg.html

docs:
	${PYTHON} ../gendoc.py sch2mag.md ../../docs/sch2mag.md

```


Excerpt from generated `.cic`:

lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic:
```json
{
    "cells": [
        {
            "class": "Cut",
            "x1": 0,
            "y1": 0,
            "x2": 3400,
            "y2": 8800,
            "layer": "",
            "net": "",
            "name": "cut_M2M4_1x2",
            "has_pr": false,
            "ckt": {},
            "children": [
                {
                    "class": "Rect",
                    "x1": 0,
                    "y1": 0,
                    "x2": 3400,
                    "y2": 8800,
                    "layer": "M2",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 300,
                    "y1": 600,
                    "x2": 3100,
                    "y2": 3400,
                    "layer": "VIA2",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 300,
                    "y1": 5400,
                    "x2": 3100,
                    "y2": 8200,
                    "layer": "VIA2",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 0,
                    "y1": 0,
                    "x2": 3400,
                    "y2": 8800,
                    "layer": "M3",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 300,
                    "y1": 600,
                    "x2": 3100,
                    "y2": 3400,
                    "layer": "VIA3",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 300,
                    "y1": 5400,
                    "x2": 3100,
                    "y2": 8200,
                    "layer": "VIA3",
                    "net": ""
                },
                {
                    "class": "Rect",
                    "x1": 0,
                    "y1": 0,
                    "x2": 3400,
                    "y2": 8800,
                    "layer": "M4",
                    "net": ""
                }
            ]
        },
        {

```


Rendered SVG from the generated layout data:

The top-cell `.cic` from `sch2mag` only contains `LELOTEMP_CMP` plus generated cut cells. For SVG rendering, the fixture uses `cicpy svg --I ...` to include the dependency libraries `JNW_ATR_SKY130A.cic` and `JNW_TR_SKY130A.cic`.

```bash
make svg
```

![](/cicpy/assets/LELOTEMP_CMP_sch2mag.svg)

