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
	rm -rf lelo_atr_sky130a
	rm -rf tech_sky130A
	-rm -rf LELOTEMP_CMP_svg LELOTEMP_CMP_svg.html

docs:
	${PYTHON} ../gendoc.py sch2mag.md ../../docs/sch2mag.md
