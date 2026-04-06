# orc

`orc` reads an ORC JSON recipe, expands the requested cell groups from a SPICE file, and writes grouped `.json` and `.spi` outputs.

<!--run_output:
run: make test && printf 'Generated files:\n' && ls -1 demo_out.json demo_out.spi
-->

Command under test:

```bash
cicpy orc demo.json
```

Input ORC recipe:

<!--cat:
file: demo.json
language: json
-->

Excerpt from generated ORC JSON:

<!--cat:
file: demo_out.json
language: json
lines: 80
-->
