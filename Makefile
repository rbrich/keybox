DIST=dist
TMPDIR=$(DIST)/zipapp.tmp

.PHONY: zipapp test cov clean
.DEFAULT: zipapp

zipapp: $(DIST)/keys.pyz

$(DIST)/keys.pyz: keys
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/keys
	cp keys/*.py $(TMPDIR)/keys
	python3 -m zipapp $(TMPDIR) -m 'keys.main:main' -p '/usr/bin/env python3' -o $@

test:
	python3 setup.py pytest --addopts "tests/"

cov:
	python3 setup.py pytest --addopts "--cov-report html --cov-report term-missing --cov=keys tests/"

htmlcov: cov
	xdg-open htmlcov/index.html

clean:
	rm -rf $(DIST)
