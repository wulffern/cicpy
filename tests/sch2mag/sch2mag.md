# sch2mag

`sch2mag` is the schematic-to-layout entrypoint. It netlists the schematic, builds the connectivity graph, runs placement and routing, and writes both Magic and `.cic` layout output.

This fixture stays standalone for CI. The test driver clones the required repositories, then runs the local `work/` flow inside `lelo_temp_sky130a`.

<!--run_output:
run: make test && printf 'Generated files:\n' && ls -1 lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.mag
-->

Command under test:

```bash
cd lelo_temp_sky130a/work
cicpy sch2mag LELO_TEMP_SKY130A LELOTEMP_CMP
```

Standalone test driver:

<!--cat:
file: Makefile
language: makefile
lines: 120
-->

Excerpt from generated `.cic`:

<!--cat:
file: lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic
language: json
lines: 80
-->

Rendered SVG from the generated layout data:

The top-cell `.cic` from `sch2mag` only contains `LELOTEMP_CMP` plus generated cut cells. For SVG rendering, the fixture uses `cicpy svg --I ...` to include the dependency libraries `JNW_ATR_SKY130A.cic` and `JNW_TR_SKY130A.cic`.

<!--run_image:
run: make svg
output_image: LELOTEMP_CMP_svg/LELOTEMP_CMP.svg
asset_name: LELOTEMP_CMP_sch2mag.svg
-->
