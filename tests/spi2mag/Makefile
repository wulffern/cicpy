PYTHON ?= python3

LIB = TEST_LIB
CELL = TOP
TECHLIB = demo

.PHONY: test clean docs svg

test:
	cd work && cicpy spi2mag top.spice ${LIB} ${CELL} --libdir ../design/ --techlib ${TECHLIB}
	@test -f design/${LIB}/${CELL}.cic
	@test -f design/${LIB}/${CELL}.mag

svg:
	cicpy svg design/${LIB}/${CELL}.cic tech/cic/${TECHLIB}.tech ${CELL}

clean:
	-rm -f design/${LIB}/${CELL}.cic design/${LIB}/${CELL}.mag
	-rm -rf ${CELL}_svg ${CELL}_svg.html

docs:
	${PYTHON} ../gendoc.py spi2mag.md ../../docs/spi2mag.md
