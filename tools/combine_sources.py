#!/usr/bin/env python3
# combine_sources.py - combine python sources into single file
#                      by inclusion of local module sources into main file
# Copyright 2015 Radek Brich

import sys
import re
import argparse

re_import = re.compile(r'^(from (\S+) import (.+)|import (\S+))$')


def get_package_path(package):
    if '.' not in sys.path:
        sys.path.append('.')
    return __import__(package).__path__[0]


def analyze(source_filename: str, package_name: str, include_sources: list):
    """Analyze `source_filename`, search for imports from `package_name`.

    Ignore those already in `include_sources`, recurse and add new ones
    into same list.

    """
    with open(source_filename, 'r') as fi:
        for line in fi:
            m = re_import.match(line)
            if not m:
                continue
            # Analyze import lines
            from_, from_list, import_mod = m.group(2, 3, 4)
            if from_ and from_.startswith(package_name + '.'):
                from_pkg, from_mod = from_.rsplit('.', 1)
                path = get_package_path(from_pkg)
                fname = '%s/%s.py' % (path, from_mod)
            elif from_ == package_name:
                fname = '%s/__init__.py' % get_package_path(package_name)
            else:
                continue
            if fname in include_sources:
                continue
            # Recursively analyze other sources
            analyze(fname, package_name, include_sources)
            include_sources.append(fname)


def combine(source_filename: str, package_name: str, include_sources: list,
            import_mods=None, import_froms=None):
    """Read `source_filename`, yield processed lines.

    Imports from `package_name` are discarded. Contents of `include_sources`
    files are pasted in place of first `package_name` import.

    """
    if import_mods is None:
        import_mods = set()
    if import_froms is None:
        import_froms = {}
    with open(source_filename, 'r') as fi:
        for line in fi:
            m = re_import.match(line)
            if not m:
                # Yield non-import lines
                yield line
                continue
            # Process import lines
            from_, from_list, import_mod = m.group(2, 3, 4)
            if from_ and (from_.startswith(package_name + '.') or
                          from_ == package_name):
                # Include sources (first time only)
                if include_sources:
                    for sub in include_sources:
                        yield '# ' + '-' * 78 + '\n'
                        for subline in combine(sub, package_name, [],
                                               import_mods, import_froms):
                            yield subline
                        yield '\n\n'
                    yield '# ' + '-' * 78 + '\n'
                    yield '# main\n'
                    yield '#\n\n'
                    include_sources = []
                # Discard imports from our package
                continue
            # Other imports - skip if seen
            if import_mod and import_mod in import_mods:
                continue
            if from_ and from_ in import_froms:
                fl = set(from_list.split(', '))
                if fl.issubset(import_froms[from_]):
                    continue
            # If not seen - output and remember
            if import_mod:
                yield line
                import_mods.add(import_mod)
                continue
            # From imports - output only unseen subset
            assert from_ is not None and from_list is not None
            from_list = from_list.split(', ')
            if from_ not in import_froms:
                # All new - output and remember
                yield line
                import_froms[from_] = set(from_list)
                continue
            # Subset
            new = [x for x in from_list if x not in import_froms[from_]]
            yield 'from %s import %s\n' % (from_, ', '.join(new))
            import_froms[from_].update(new)


def main():
    ap = argparse.ArgumentParser(description="combine sources into single file")
    ap.add_argument('-i', dest="input_file", default='pwlockr.py',
                    help="input file name")
    ap.add_argument('-o', dest="output_file", default='pwlockr-static.py',
                    help="output file name")
    ap.add_argument('--package', default='pwlockr',
                    help="python package to be combined")
    args = ap.parse_args()

    include_sources = []
    print("Analyzing %r..." % args.input_file)
    analyze(args.input_file, args.package, include_sources)
    print("Sources to include:", '\n'.join(include_sources), sep='\n')
    empty_lines_in_row = 0
    with open(args.output_file, 'w') as fo:
        for line in combine(args.input_file, args.package, include_sources):
            if not line.strip():
                empty_lines_in_row += 1
            else:
                empty_lines_in_row = 0
            if empty_lines_in_row < 3:
                fo.write(line)
    print("Written to %r." % args.output_file)


if __name__ == '__main__':
    main()
