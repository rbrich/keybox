# Keybox
# (keybox file manager)
#

import time
import itertools
import json

from .envelope import Envelope
from .envelope_gpg import EnvelopeGPG
from .record import Record, COLUMNS
from .fileformat import format_file, parse_file, write_file
from .stringutil import nt_escape

IMPORT_MIN_MATCHED_COLS = 3


class EncryptedRecord:

    """Augmented record with special handling of password.

    It needs Keybox instance for on-access password decryption.

    """

    def __init__(self, keybox, record: Record):
        self._keybox = keybox
        self._record = record

    def __repr__(self):
        a = ('{}={!r}'.format(column, self[column])
             for column in self._record.get_columns())
        return "{}({})".format(self.__class__.__name__, ', '.join(a))

    def __setitem__(self, key, value):
        value = str(value) if value else ''
        if key == 'password':
            value = self._keybox.envelope.encrypt_base64(value)
        self._record[key] = value

    def __getitem__(self, key):
        value = self._record[key]
        if key == 'password' and value:
            value = self._keybox.envelope.decrypt_base64(value)
        return value

    def __len__(self):
        return len(self._record)

    def get(self, key, default=None):
        value = self._record.get(key, default)
        if key == 'password' and value:
            value = self._keybox.envelope.decrypt_base64(value)
        return value

    def keys(self):
        return self._record.keys()

    def get_columns(self):
        return self._record.get_columns()

    @property
    def wrapped_record(self):
        return self._record


class KeyboxRecord(EncryptedRecord):

    """Augmented record with special handling of mtime, password and __str__.

    The augmentations are dependent on Keybox instance.

    * mtime: Updated to current time when any other item is changed.
    * password: Contains encrypted password, decrypted on access.

    Str presentation of record uses column width info from Keybox
    to format all records into nice table.

    """

    def __init__(self, keybox, record: Record):
        EncryptedRecord.__init__(self, keybox, record)
        if not record['mtime']:
            self.touch()
        for key, value in record.items():
            self._keybox.update_width(key, value)

    def __str__(self):
        a = []
        for column in self._record.get_columns():
            if column != 'password':
                width = self._keybox.get_column_width(column)
                value = self._record[column]
                a.append(value.ljust(width))
        return ''.join(a)

    def __setitem__(self, key, value):
        if key == 'mtime':
            raise Exception('Cannot set mtime directly.')
        EncryptedRecord.__setitem__(self, key, value)
        value = str(value) if value else ''
        self._keybox.update_width(key, value)
        self.touch()

    def touch(self):
        mtime = time.strftime('%F %T')
        self._record['mtime'] = mtime
        self._keybox.update_width('mtime', mtime)
        self._keybox.touch()


class ExportRecord(EncryptedRecord):

    def __init__(self, keybox, record: Record):
        EncryptedRecord.__init__(self, keybox, record)

    def __getitem__(self, key):
        value = EncryptedRecord.__getitem__(self, key)
        if key == 'password':
            return nt_escape(value)
        return value


class Keybox:

    """Keybox file manager.

    All public methods are part of public API.

    """

    def __init__(self):
        """Initialize the keybox, using `passphrase`.

        In next step, call `read` to read existing file
        or call `write` to create new empty file.

        """
        self._records = []
        self._columns = COLUMNS
        self._column_widths = {}
        self._envelope = Envelope()
        #: Are there any unwritten changes?
        self._modified = False

    def __iter__(self):
        return (KeyboxRecord(self, record) for record in self._records)

    def __getitem__(self, item):
        return KeyboxRecord(self, self._records[item])

    def __len__(self):
        return len(self._records)

    @property
    def envelope(self):
        return self._envelope

    @property
    def raw_records(self):
        return self._records

    def set_passphrase(self, new_passphrase):
        """Set new passphrase to keybox and re-encrypt all record passwords."""
        previous = self._envelope
        self._envelope = Envelope()
        self._envelope.set_passphrase(new_passphrase)
        for record in self._records:
            password = previous.decrypt_base64(record['password'])
            record['password'] = self._envelope.encrypt_base64(password)
        self._modified = True

    def check_passphrase(self, passphrase):
        return self._envelope.check_passphrase(passphrase)

    def get_columns(self, start_text=None):
        if start_text is None or len(self._columns) == 0:
            return self._columns
        return [c for c in self._columns if c.startswith(start_text.lower())]

    def get_column_width(self, column):
        return self._column_widths[column]

    def get_column_values(self, column):
        return set(record[column] for record in self._records if record.get(column))

    def get_tags(self, start_text=None):
        start_text = (start_text or '').lower()
        all_tags = set(itertools.chain.from_iterable(
            record['tags'].split() for record in self._records))
        return [t for t in sorted(all_tags) if t.startswith(start_text)]

    def read(self, file, passphrase_cb):
        """Read keybox records from encrypted `file`."""
        data = self._envelope.read(file, passphrase_cb)
        self._records, self._columns = parse_file(data.decode('utf-8'))
        self._modified = False
        self.recompute_widths()

    def write(self, file):
        """Write keybox records to encrypted `file`."""
        data = format_file(self._records, self._columns)
        self._envelope.write(file, data.encode('utf-8'))
        self._modified = False
        for record in self._records:
            record.modified = False

    def export_file(self, file, file_format):
        """Write decrypted records to plain-text `file`."""
        if file_format == 'plain':
            records = (ExportRecord(self, record) for record in self._records)
            write_file(file, records, self._columns)
        elif file_format == 'json':
            json.dump([dict(EncryptedRecord(self, record)) for record in self._records], file)
        else:
            raise NotImplementedError(f"{file_format} export not implemented")

    def import_file(self, file, file_format, fn_passphrase, fn_resolve_matched_rec, fn_print_new):
        """Import non-identical records from `file` which is in `file_format`.

        Checks all incoming records:
        - identical records are skipped
        - modified records are updated or added (see below)
        - new records are added
        - missing records - ignored

        Modified records:
        - detected at least 4 columns with same values
        - options: keep local, replace with incoming, add incoming as new

        """
        if file_format in ('keybox', 'keybox_gpg'):
            # decrypt the input file
            input_envelope = EnvelopeGPG() if file_format == 'keybox_gpg' else Envelope()
            data = input_envelope.read(file, fn_passphrase)
            # parse the input file
            records, columns = parse_file(data.decode('utf-8'))

            # fake Keybox object for input file
            class FakeKeybox:
                pass

            input_keybox = FakeKeybox()
            input_keybox.envelope = input_envelope

            for i, record in enumerate(records):
                records[i] = EncryptedRecord(input_keybox, record)

        elif file_format == 'plain':
            records, columns = parse_file(file.read().decode('utf-8'))

        elif file_format == 'json':
            records = json.load(file)
            if len(records):
                columns = tuple(records[0].keys())
            else:
                columns = ()

        else:
            raise NotImplementedError(f"{file_format} import not implemented")

        assert set(columns).issubset(self._columns), \
            'Unexpected column in header: %s' \
            % (set(columns) - set(self._columns))
        n_new = 0
        n_updated = 0
        candidates = [EncryptedRecord(self, record) for record in self._records]
        for n, new_rec in enumerate(records):
            matched_recs, exact = self._match_record(candidates, new_rec)
            if exact:
                assert len(matched_recs) == 1
                candidates.remove(matched_recs[0])
                continue
            if not matched_recs:
                # new
                fn_print_new(new_rec)
                self.add_record(**new_rec)
                self.touch()
                n_new += 1
                continue
            # updated - give options
            rec, resolution = fn_resolve_matched_rec(matched_recs, new_rec)
            if resolution == 'replace':
                for column in self._columns:
                    rec[column] = new_rec[column]
                candidates.remove(rec)
                n_updated += 1
                self.touch()
            elif resolution == 'add':
                self.add_record(**new_rec)
                n_new += 1
                self.touch()
            elif resolution != 'keep_local':
                raise ValueError(f"unknown resolution: {resolution}")
        return len(records), n_new, n_updated

    def touch(self):
        self._modified = True

    def modified(self):
        """True if keybox was modified since last read/write."""
        return self._modified

    def add_record(self, **kwargs) -> KeyboxRecord:
        """Add and return new record.

        Use keyword arguments to set initial column values.

        """
        password = kwargs.pop('password', '')
        record = Record(columns=self._columns, **kwargs)
        if password:
            record['password'] = self._envelope.encrypt_base64(password)
        self._records.append(record)
        return KeyboxRecord(self, record)

    def delete_record(self, record: KeyboxRecord):
        """Delete record previously obtained by other methods."""
        self._records.remove(record.wrapped_record)
        self._modified = True

    def recompute_widths(self):
        for column in self._columns:
            w = 2
            if self._records:
                w += max(len(record[column]) for record in self._records)
            self._column_widths[column] = w

    def update_width(self, column, value):
        new_width = len(value) + 2
        if new_width > self._column_widths.get(column, 0):
            self._column_widths[column] = new_width

    def _match_record(self, candidates, other, min_score=IMPORT_MIN_MATCHED_COLS):
        """Look for most similar record to `other`.

        :param min_score: Minimal number of matching columns
        :returns: (matching_recs, exact_match)

        """
        matching = []
        max_score = len(self._columns)
        columns_without_password = tuple(c for c in self._columns if c != 'password')
        for rec in candidates:
            score = 0
            # compare all columns except password and check score against min_score
            for column in columns_without_password:
                if rec[column] == other.get(column, ''):
                    score += 1
            if score + 1 < min_score:
                continue
            # optimization: compare password separately
            # (many recs are skipped by previous check)
            if rec['password'] == other['password']:
                score += 1
            if score < min_score:
                continue
            # identical record -> exact match
            if score == max_score:
                return [rec], True
            # increase min_score, drop candidates under this level later
            if score > min_score:
                min_score = score
                matching.clear()
            matching.append(rec)
        return matching, False
