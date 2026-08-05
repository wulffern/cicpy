test:
	cicpy transpile SAR9B_CV.cic.gz demo.tech SAR9B --layskill --schskill --verilog --xschem --spice --winfo --rinfo demo.txt --magic
	python3 check_bbox.py SAR9B_CV.cic.gz SAR9B

clean:
	-rm *.spice
	-rm *.spi
	-rm *.yaml
	-rm -rf SAR9B
	-rm *.il
	-rm *.v

docs:
	${PYTHON} ../gendoc.py transpile.md ../../docs/transpile.md
