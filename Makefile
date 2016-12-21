DIST=dist
TMPDIR=$(DIST)/zipapp.tmp

.PHONY: zipapp test cov clean
.DEFAULT: zipapp

zipapp: $(DIST)/keybox.pyz

$(DIST)/keybox.pyz: keybox
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/keybox
	cp keybox/*.py $(TMPDIR)/keybox
	python3 -m zipapp $(TMPDIR) -m 'keybox.main:main' -p '/usr/bin/env python3' -o $@

test:
	python3 setup.py pytest --addopts "tests/"

cov:
	python3 setup.py pytest --addopts "--cov-report html --cov-report term-missing --cov=keybox tests/"

htmlcov: cov
	xdg-open htmlcov/index.html

clean:
	rm -rf $(DIST)
