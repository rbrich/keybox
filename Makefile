BUILD=build
VERSION=$(shell cat VERSION)
ZIPAPP=$(BUILD)/zipapp

.PHONY: build zipapp cryptoref test cov htmlcov check upload clean

build: dist/keybox-$(VERSION).tar.gz
zipapp: $(BUILD)/keybox.pyz

dist/keybox-$(VERSION).tar.gz:
	python3 setup.py sdist bdist_wheel

$(BUILD)/keybox.pyz: keybox
	rm -rf $(ZIPAPP)
	mkdir -p $(ZIPAPP)/keybox
	cp keybox/*.py $(ZIPAPP)/keybox
	python3 -m zipapp $(ZIPAPP) -m 'keybox.main:main' -p '/usr/bin/env python3' -o $@

cryptoref: cryptoref/cryptoref.pyx
	python3 setup.py build_ext --inplace

test:
	python3 setup.py pytest --addopts "tests/"

cov:
	python3 setup.py pytest --addopts "--cov-report html --cov-report term-missing --cov=keybox tests/"

htmlcov: cov
	xdg-open htmlcov/index.html

check: build
	twine check dist/*

upload: build
	twine upload dist/*

clean:
	rm -rf $(BUILD) dist keybox.egg-info cryptoref/cryptoref.c cryptoref.cpython-*.so
