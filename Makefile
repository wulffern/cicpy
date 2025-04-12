
testdir = tests
dirs =  ${testdir}/jcell \
	${testdir}/place \
	${testdir}/sch2mag \
	${testdir}/svg \
	${testdir}/transpile \
	${testdir}/minecraft

cwd = ${shell pwd}

.PHONY: docs build tests

tests:
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && echo "\n#INFO: Testing ${d}\n"  && make test || exit  ;}

build:
	python3 -m build

test_upload:
	python3 -m twine upload -u __token__ --repository testpypi dist/*

upload:
	python3 -m twine upload -u __token__ --repository pypi dist/*
