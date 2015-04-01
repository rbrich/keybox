DIST=dist
3TO2=3to2
COVERAGE=coverage
COMBINE=tools/combine_sources.py

.PHONY: static33 static32 static27 test coverage clean
.DEFAULT: static33

static33: $(DIST)/pwlockr-static33.py
static32: $(DIST)/pwlockr-static32.py
static27: $(DIST)/pwlockr-static27.py

$(DIST)/pwlockr-static33.py: pwlockr.py
	mkdir -p $(DIST)
	$(COMBINE) -i $< -o $@
	chmod +x $@

$(DIST)/pwlockr-static32.py: pwlockr.py
	mkdir -p $(DIST)
	$(COMBINE) -i $< -o $@.tmp
	sed -i $@.tmp -r -e '/^try:/N;N;N;N;s/try:\s*from inspect .*(from funcsigs .*)/\1/'
	$(COMBINE) -i $@.tmp -o $@ --package funcsigs
	sed -i $@ -r -e 's/^from __future__ .*//'
	rm $@.tmp
	chmod +x $@

# EXPERIMENTAL conversion for Python 2.7
# There are still many unresolved unicode errors
$(DIST)/pwlockr-static27.py: pwlockr.py
	mkdir -p $(DIST)
	$(COMBINE) -i $< -o $@
	$(3TO2) -fprintfunction -nw --no-diffs $@
	$(3TO2) -fall -xprint -nw --no-diffs $@
	sed -i $@ -r -e 's/import math/\0\nmath.log2 = lambda x: math.log(x, 2)/'
	sed -i $@ -e '/cmdline.split(None, 1))/N;s/\(cmdline.split(None, 1))\)\n/\1; /'
	sed -i $@ -e "s/\.decode()/\.decode('utf8')/"
	sed -i $@ -r -e 's,(#!/usr/bin/env python)3,\1,'
	chmod +x $@

test:
	python3 -m unittest discover -s tests

coverage:
	$(COVERAGE) run -m unittest discover -s tests
	$(COVERAGE) html
	$(COVERAGE) report

clean:
	rm -f $(DIST)/pwlockr-*.py
