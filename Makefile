DIST=dist
TMPDIR=$(DIST)/zipapp.tmp
3TO2=3to2
COVERAGE=coverage
COMBINE=tools/combine_sources.py

.PHONY: zipapp33 zipapp32 test coverage clean
.DEFAULT: zipapp33

zipapp33: $(DIST)/pwlockr-zipapp33.pyz
zipapp32: $(DIST)/pwlockr-zipapp32.pyz

$(DIST)/pwlockr-zipapp33.pyz: pwlockr
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/pwlockr
	cp pwlockr/*.py $(TMPDIR)/pwlockr
	python3 -m zipapp $(TMPDIR) -m 'pwlockr.main:main' -p '/usr/bin/env python3' -o $@

$(DIST)/pwlockr-zipapp32.pyz: pwlockr
	rm -rf $(TMPDIR)
	mkdir -p $(TMPDIR)/pwlockr
	cp pwlockr/*.py $(TMPDIR)/pwlockr
	pip3 download --isolated -q --no-deps -d $(TMPDIR) funcsigs
	unzip $(TMPDIR)/funcsigs-*.whl -d $(TMPDIR)
	rm $(TMPDIR)/funcsigs-*.whl
	rm -rf $(TMPDIR)/funcsigs-*-info/
	python3 -m zipapp $(TMPDIR) -m 'pwlockr.main:main' -p '/usr/bin/env python3' -o $@

test:
	python3 -m unittest discover -s tests

coverage:
	$(COVERAGE) run -m unittest discover -s tests
	$(COVERAGE) html
	$(COVERAGE) report

clean:
	rm -rf $(DIST)
