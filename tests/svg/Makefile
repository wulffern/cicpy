
test:
	cicpy svg ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech SAR9B

clean:
	-rm -rf SAR9B_svg
	-rm *.html

docs:
	${PYTHON} ../gendoc.py svg.md ../../docs/svg.md
