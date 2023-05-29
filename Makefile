

build:
	python3 -m build

test_upload:
	python3 -m twine upload -u wulffern --repository testpypi dist/*

upload:
	python3 -m twine upload -u wulffern --repository pypi dist/*
