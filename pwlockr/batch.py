# LockerBatch
# (import / export)
#

from pwlockr.locker import Locker, LockerRecord
from pwlockr.fileformat import format_header, format_record, parse_file


class LockerBatch(Locker):

    """Extended password locker with import/export functionality."""

    def export(self):
        columns = self._columns
        print(format_header(columns), end='')
        for record in self._records:
            record_proxy = LockerRecord(self, record)
            print(format_record(record_proxy, columns), end='')

    def import_file(self, filename):
        with open(filename, 'rb') as f:
            records, columns = parse_file(f)
        assert set(columns).issubset(self._columns),\
            'Unexpected column in header: %s'\
            % (set(columns) - set(self._columns))
        imported = 0
        for record in records:
            if self._check_import(record):
                record['password'] = self.encrypt_password(record['password'])
                self._records.append(record)
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
