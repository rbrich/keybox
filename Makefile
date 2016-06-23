DIST=dist
TMPDIR=$(DIST)/zipapp.tmp

.PHONY: zipapp33 zipapp32 test cov clean
.DEFAULT: zipapp33

zipapp33: $(DIST)/keys-zipapp33.pyz
zipapp32: $(DIST)/keys-zipapp32.pyz

$(DIST)/keys-zipapp33.pyz: keys
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/keys
	cp keys/*.py $(TMPDIR)/keys
	python3 -m zipapp $(TMPDIR) -m 'keys.main:main' -p '/usr/bin/env python3' -o $@

$(DIST)/keys-zipapp32.pyz: keys
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/keys
	cp keys/*.py $(TMPDIR)/keys
	pip3 download --isolated -q --no-deps -d $(TMPDIR) funcsigs
	unzip $(TMPDIR)/funcsigs-*.whl -d $(TMPDIR)
	rm $(TMPDIR)/funcsigs-*.whl
	rm -rf $(TMPDIR)/funcsigs-*-info/
	python3 -m zipapp $(TMPDIR) -m 'keys.main:main' -p '/usr/bin/env python3' -o $@

test:
	python3 setup.py pytest --addopts "tests/"

cov:
	python3 setup.py pytest --addopts "--cov-report html --cov-report term-missing --cov=keys tests/"

htmlcov: cov
	xdg-open htmlcov/index.html

clean:
	rm -rf $(DIST)
