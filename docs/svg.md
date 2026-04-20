# svg

`svg` renders every cell in a `.cic` library into standalone SVG files and an index HTML page.

It also supports extra library inputs through `--I`, which is useful when the top-level `.cic` only contains one generated cell and references child cells from other libraries.

```bash
make test
```

![](/cicpy/assets/NCHDL_svg_test.svg)


Representative top-level SVG:

![](/cicpy/assets/ALGIC001_SAR9B_CV_svg_test.svg)


Representative primitive SVG:

![](/cicpy/assets/NCHDL_svg_test.svg)

