# KeyboxBatch
# (import / export)
#

import sys

from keybox.keybox import Keybox
from keybox.fileformat import write_file, read_file


class KeyboxBatch(Keybox):

    """Extended keybox with import/export functionality."""

    def export_file(self, filename):
        if filename == '-':
            write_file(sys.stdout, self, self._columns)
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                write_file(f, self, self._columns)

    def import_file(self, filename):
        if filename == '-':
            records, columns = read_file(sys.stdin)
        else:
            with open(filename, 'r', encoding='utf-8') as f:
                records, columns = read_file(f)
        assert set(columns).issubset(self._columns),\
            'Unexpected column in header: %s'\
            % (set(columns) - set(self._columns))
        imported = 0
        for record in records:
            if self._check_import(record):
                self.add_record(**record)
                imported += 1
        return len(records), imported

    def _check_import(self, new_record):
        def cmp_with_new(rec):
            # Test all columns but mtime and password
            if all(rec[c] == new_record.get(c, '') for c in
                   ('site', 'user', 'url', 'tags', 'note')):
                # Everything same, now test the password too
                password = self.decrypt_password(rec['password'])
                if password == new_record['password']:
                    return True
            # One of tests failed, not same records
            return False
        return not any(cmp_with_new(record) for record in self._records)
