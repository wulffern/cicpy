# spi2mag

`spi2mag` reads a SPICE subcircuit, resolves referenced Magic cells from a library path, places the layout, and writes both `.mag` and `.cic` output.

<!--run_output:
run: make test && printf 'Generated files:\n' && ls -1 design/TEST_LIB/TOP.cic design/TEST_LIB/TOP.mag
-->

Command under test:

```bash
cd work
cicpy spi2mag top.spice TEST_LIB TOP --libdir ../design/ --techlib demo
```

Input SPICE fixture:

<!--cat:
file: work/top.spice
language: spice
-->

Excerpt from generated Magic layout:

<!--cat:
file: design/TEST_LIB/TOP.mag
language: text
lines: 80
-->

Rendered SVG from the generated `.cic`:

<!--run_image:
run: make svg
output_image: TOP_svg/TOP.svg
asset_name: TOP_spi2mag.svg
-->
