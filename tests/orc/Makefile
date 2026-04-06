PYTHON ?= python3

.PHONY: test clean docs

test:
	cicpy orc demo.json
	@test -f demo_out.json
	@test -f demo_out.spi

clean:
	-rm -f demo_out.json demo_out.spi

docs:
	${PYTHON} ../gendoc.py orc.md ../../docs/orc.md
