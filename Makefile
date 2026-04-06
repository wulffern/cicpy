PYTHON ?= python3

testdir = tests
dirs = ${testdir}/jcell \
	${testdir}/place \
	${testdir}/routes \
	${testdir}/sch2mag \
	${testdir}/spi2mag \
	${testdir}/orc \
	${testdir}/filter \
	${testdir}/svg \
	${testdir}/transpile \
	${testdir}/minecraft

docs = ${testdir}/index ${testdir}/routes ${testdir}/jcell ${testdir}/svg ${testdir}/transpile ${testdir}/minecraft ${testdir}/sch2mag

cwd = ${shell pwd}

.PHONY: docs build test tests unit_test clean

docs:
	${foreach d, ${docs}, cd ${cwd}; cd ${d} && make docs PYTHON=${PYTHON} || exit  ;}

unit_test:
	@true

test: unit_test
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && echo "\n#INFO: Testing ${d}\n" && make test PYTHON=${PYTHON} || exit  ;}

tests: test

clean:
	${foreach d, ${dirs} ${docs}, cd ${cwd}; cd ${d} && make clean PYTHON=${PYTHON} >/dev/null 2>&1 || true ;}

build:
	${PYTHON} -m build

test_upload:
	${PYTHON} -m twine upload -u __token__ --repository testpypi dist/*

upload:
	${PYTHON} -m twine upload -u __token__ --repository pypi dist/*

JEKYLL_VERSION=3.8
SITE=${shell pwd}/docs
BUNDLE_CACHE ?= ${HOME}/.cache/cicpy-jekyll-bundle
jstart:
	mkdir -p "${BUNDLE_CACHE}"
	docker run --rm --name cicsim_docs \
		--volume="${SITE}:/srv/jekyll" \
		--volume="${BUNDLE_CACHE}:/usr/local/bundle" \
		-p 3002:4000 -it jekyll/jekyll:${JEKYLL_VERSION} \
		jekyll serve --watch --drafts --incremental
