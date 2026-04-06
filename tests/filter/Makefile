PYTHON ?= python3

.PHONY: test clean docs

test:
	cicpy filter ../sch2mag/lelo_temp_sky130a/design/LELO_TEMP_SKY130A/LELOTEMP_CMP.cic LELOTEMP_CMP \
		--I ../sch2mag/jnw_atr_sky130a/design/JNW_ATR_SKY130A.cic \
		--I ../sch2mag/jnw_tr_sky130a/design/JNW_TR_SKY130A.cic > filter.stdout
	@test ! -s filter.stdout
	@printf 'Parsed LELOTEMP_CMP.cic with included libraries and no CLI output.\n' > filter.status

clean:
	-rm -f filter.stdout filter.status

docs:
	${PYTHON} ../gendoc.py filter.md ../../docs/filter.md
