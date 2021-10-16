
DIR = ${shell ls -d1 */}

all: ${DIR}
	${foreach d, ${DIR}, cd ${d}; make && make clean; cd ..;}
