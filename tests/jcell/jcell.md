# jcell

`jcell` extracts one cell from a `.cic` file and prints the JSON for that cell.

<!--run_output:
run: make test && wc -l NCHDL.json
-->

Command under test:

```bash
cicpy jcell ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech NCHDL > NCHDL.json
```

Excerpt from the extracted cell JSON:

<!--cat:
file: NCHDL.json
language: json
lines: 80
-->
