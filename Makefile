BUILD=build
VERSION=$(shell cat VERSION)
ZIPAPP=$(BUILD)/zipapp

.PHONY: build zipapp cryptoref test cov htmlcov check upload clean

build: dist/keybox-$(VERSION).tar.gz
zipapp: $(BUILD)/keybox.pyz

dist/keybox-$(VERSION).tar.gz:
	python3 -m build

$(BUILD)/keybox.pyz: keybox
	rm -rf $(ZIPAPP)
	mkdir -p $(ZIPAPP)
	cp -r keybox $(ZIPAPP)
	python3 -m zipapp $(ZIPAPP) -m 'keybox.main:main' -p '/usr/bin/env python3' -o $@

cryptoref: cryptoref/cryptoref.pyx
	python3 setup.py build_ext --inplace

test:
	python3 -m pytest

.coverage: keybox tests .coveragerc
	python3 -m coverage run -m pytest

cov: .coverage
	python3 -m coverage report --show-missing --fail-under=70

htmlcov: .coverage
	python3 -m coverage html --show-contexts
	open htmlcov/index.html

check: build
	twine check dist/*

upload: build
	twine upload dist/*

clean:
	rm -rf $(BUILD) dist keybox.egg-info \
		cryptoref/cryptoref.c cryptoref.cpython-*.so \
		.coverage
