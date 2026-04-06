# svg

`svg` renders every cell in a `.cic` library into standalone SVG files and an index HTML page.

It also supports extra library inputs through `--I`, which is useful when the top-level `.cic` only contains one generated cell and references child cells from other libraries.

<!--run_image:
run: make test
output_image: SAR9B_svg/NCHDL.svg
asset_name: NCHDL_svg_test.svg
-->

Representative top-level SVG:

<!--copy_image:
output_image: SAR9B_svg/ALGIC001_SAR9B_CV.svg
asset_name: ALGIC001_SAR9B_CV_svg_test.svg
-->

Representative primitive SVG:

<!--copy_image:
output_image: SAR9B_svg/NCHDL.svg
asset_name: NCHDL_svg_test.svg
-->
