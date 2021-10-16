
all: diffpair horz vert

diffpair:
	cicpy place ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  diffpair.csv

horz:
	cicpy place ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  horz.csv --circuit horizontal

vert:
	cicpy place ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  vert.csv --circuit vertical

clean:
	-rm *_place.csv
	-rm *.il
