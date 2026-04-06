# filter

`filter` currently acts as a parse-only smoke test. It loads a `.cic` design, optionally merges included library `.cic` files through `--I`, and exits without producing a transformed output artifact yet.

<!--run_output:
run: make test && cat filter.status && printf 'stdout bytes: ' && wc -c < filter.stdout
-->

Command under test:

```bash
cicpy filter ../sch2mag/lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic LELOTEMP_CMP \
  --I ../sch2mag/jnw_atr_sky130a/design/JNW_ATR_SKY130A.cic \
  --I ../sch2mag/jnw_tr_sky130a/design/JNW_TR_SKY130A.cic
```

Fixture excerpt:

<!--cat:
file: ../sch2mag/lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic
language: json
lines: 60
-->
