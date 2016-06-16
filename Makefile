DIST=dist
TMPDIR=$(DIST)/zipapp.tmp
3TO2=3to2
COVERAGE=coverage

.PHONY: zipapp33 zipapp32 test coverage clean
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
	python3 -m unittest discover -s tests

coverage:
	$(COVERAGE) run -m unittest discover -s tests
	$(COVERAGE) html
	$(COVERAGE) report

clean:
	rm -rf $(DIST)
