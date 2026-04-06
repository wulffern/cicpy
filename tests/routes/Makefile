PYTHON ?= /opt/eda/python3/bin//python3

ARTIFACTS = ROUTE_DEMOS_svg ROUTE_DEMOS_svg.html route_examples.cic.gz
SVGS = \
	ROUTE_DEMOS_svg/ROUTE_STRAIGHT.svg \
	ROUTE_DEMOS_svg/ROUTE_STRAIGHT_WITH_CUTS.svg \
	ROUTE_DEMOS_svg/ROUTE_STRAIGHT_WITH_FILLHCUT.svg \
	ROUTE_DEMOS_svg/ROUTE_LEFT.svg \
	ROUTE_DEMOS_svg/ROUTE_RIGHT.svg \
	ROUTE_DEMOS_svg/ROUTE_VERTICAL.svg \
	ROUTE_DEMOS_svg/ROUTE_VERTICAL_ANTENNA.svg \
	ROUTE_DEMOS_svg/ROUTE_U_LEFT.svg \
	ROUTE_DEMOS_svg/ROUTE_U_RIGHT.svg \
	ROUTE_DEMOS_svg/ROUTE_U_TOP.svg \
	ROUTE_DEMOS_svg/ROUTE_U_BOTTOM.svg \
	ROUTE_DEMOS_svg/ROUTE_LEFT_DOWN_LEFT_UP.svg \
	ROUTE_DEMOS_svg/ROUTE_LULD.svg \
	ROUTE_DEMOS_svg/ROUTE_STRAP_HORIZONTAL.svg \
	ROUTE_DEMOS_svg/ROUTE_STRAP_VERTICAL.svg \
	ROUTE_DEMOS_svg/ROUTE_ORTHOGONAL.svg

run:
	PYTHONPATH=../../src ${PYTHON} build_route_examples.py

test: run
	test -f route_examples.cic.gz
	@for f in ${SVGS}; do test -f $$f || exit 1; done

test_clean:
	-rm -rf ${ARTIFACTS}

clean: test_clean

docs:
	${PYTHON} ../gendoc.py routes.md ../../docs/routes.md
