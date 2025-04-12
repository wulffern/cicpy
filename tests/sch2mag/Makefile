

jnw_gr07_sky130a:
	git clone https://github.com/analogicus/jnw_gr07_sky130a jnw_gr07_sky130a
	cd jnw_gr07_sky130a && git checkout 33e4575ccc73247f1a61bcef9550a16c9e5c8921
	git clone https://github.com/analogicus/jnw_tr_sky130a jnw_tr_sky130a
	git clone https://github.com/analogicus/jnw_atr_sky130a jnw_atr_sky130a
	git clone https://github.com/wulffern/tech_sky130A tech_sky130A

test: jnw_gr07_sky130a
	cd jnw_gr07_sky130a && git reset --hard
	cd jnw_gr07_sky130a/work && cicpy sch2mag JNW_GR07_SKY130A amplifier

clean:
	rm -rf jnw_gr07_sky130a
	rm -rf jnw_tr_sky130a
	rm -rf jnw_atr_sky130a
	rm -rf tech_sky130A
