
test:
	cicpy jcell ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  NCHDL > NCHDL.json

clean:
	-rm *.json

docs:
	${PYTHON} ../gendoc.py jcell.md ../../docs/jcell.md
