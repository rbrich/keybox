# Keybox
# (keybox file manager)
#

import base64
import time
import itertools

from keybox.gpg import encrypt, decrypt
from keybox.record import Record, COLUMNS
from keybox.fileformat import format_file, parse_file, write_file, read_file


class EncryptedRecord:

    """Augmented record with special handling of password.

    It needs Keybox instance for on-access password decryption.

    """

    def __init__(self, keybox, record: Record):
        self._keybox = keybox
        self._record = record

    def __repr__(self):
        a = ['{}={!r}'.format(column, self[column])
             for column in self._record.get_columns()]
        return "{}({})".format(self.__class__.__name__, ', '.join(a))

    def __setitem__(self, key, value):
        value = str(value) if value else ''
        if key == 'password':
            value = self._keybox.encrypt_password(value)
        self._record[key] = value

    def __getitem__(self, key):
        value = self._record[key]
        if key == 'password' and value:
            value = self._keybox.decrypt_password(value)
        return value

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


class Keybox:

    """Keybox file manager.

    All public methods are part of public API.

    """

    def __init__(self, passphrase=None):
        """Initialize the keybox, using `passphrase`.

        In next step, call `read` to read existing file
        or call `write` to create new empty file.

        """
        self._records = []
        self._columns = COLUMNS
        self._column_widths = {}
        self._passphrase = passphrase
        #: Are there any unwritten changes?
        self._modified = False

    def __iter__(self):
        return (KeyboxRecord(self, record) for record in self._records)

    def __getitem__(self, item):
        return KeyboxRecord(self, self._records[item])

    def __len__(self):
        return len(self._records)

    @property
    def raw_records(self):
        return self._records

    def set_passphrase(self, new_passphrase):
        """Set new passphrase to keybox and re-encrypt all record passwords."""
        for record in self._records:
            password = self.decrypt_password(record['password'])
            record['password'] = self.encrypt_password(password, new_passphrase)
        self._passphrase = new_passphrase
        self._modified = True

    def check_passphrase(self, passphrase):
        return self._passphrase == passphrase

    def get_columns(self, start_text=None):
        start_text = start_text.lower() or ''
        return [c for c in self._columns if c.startswith(start_text)]

    def get_column_width(self, column):
        return self._column_widths[column]

    def get_column_values(self, column, start_text=None):
        start_text = (start_text or '').lower()
        return sorted(record[column] for record in self._records
                      if record[column].startswith(start_text))

    def get_tags(self, start_text=None):
        start_text = (start_text or '').lower()
        all_tags = set(itertools.chain.from_iterable(
            record['tags'].split() for record in self._records))
        return [t for t in sorted(all_tags) if t.startswith(start_text)]

    def read(self, file):
        """Read keybox records from encrypted `file`."""
        data = file.read()
        data = decrypt(data, self._passphrase).decode('utf-8')
        self._records, self._columns = parse_file(data)
        self._modified = False
        self.recompute_widths()

    def write(self, file):
        """Write keybox records to encrypted `file`."""
        data = format_file(self._records, self._columns).encode('utf-8')
        data = encrypt(data, self._passphrase)
        file.write(data)
        self._modified = False
        for record in self._records:
            record.modified = False

    def dump_file(self, file):
        """Write decrypted records to plain-text `file`."""
        write_file(file, self, self._columns)

    def import_file(self, file, fn_resolve_matched_rec):
        """Import non-identical records from plain-text `file`.

        Checks all incoming records:
        - identical records are skipped
        - modified records are updated or added (see bellow)
        - new records are added
        - missing records - ignored

        Modified records (TODO):
        - same site and/or url
        - same user
        - different mtime
        - options: keep local, replace with incoming, add incoming as new

        """
        # Is the imported file encrypted?
        # TODO
        #
        records, columns = read_file(file)
        assert set(columns).issubset(self._columns), \
            'Unexpected column in header: %s' \
            % (set(columns) - set(self._columns))
        n_new = 0
        n_updated = 0
        candidates = [EncryptedRecord(self, record) for record in self._records]
        for n, new_rec in enumerate(records):
            matched_recs, score = self._match_record(candidates, new_rec)
            if score == 1.0:
                assert len(matched_recs) == 1
                candidates.remove(matched_recs[0])
                continue
            if not matched_recs or score < 0.5:
                # new
                print("new:", new_rec)
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
            else:
                assert resolution == 'keep_local'
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
            record['password'] = self.encrypt_password(password)
        self._records.append(record)
        return KeyboxRecord(self, record)

    def delete_record(self, record: KeyboxRecord):
        """Delete record previously obtained by other methods."""
        self._records.remove(record.wrapped_record)
        self._modified = True

    def decrypt_password(self, password_data: str):
        """Decrypt and return password from record."""
        data = base64.b64decode(password_data.encode(), validate=True)
        return decrypt(data, self._passphrase).decode()

    def encrypt_password(self, password: str, encrypt_passphrase=None):
        """Encrypt the password and return it."""
        data = encrypt(password.encode(),
                       encrypt_passphrase or self._passphrase,
                       s2k_count=0)
        return base64.b64encode(data).decode()

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

    def _match_record(self, candidates, other):
        """Look for most similar record to `other`."""
        def column_matches(name):
            return rec[name] == other.get(name, '')
        scored = []
        min_score = 1
        max_score = len(self._columns)
        for rec in candidates:
            score = 0
            for column in self._columns:
                if rec[column] == other.get(column, ''):
                    score += 1
            if score == max_score:
                # Identical
                return [rec], score / max_score
            if score >= min_score:
                min_score = score
            scored.append((score, rec))
        recs = [rec for score, rec in scored if score == min_score]
        return recs, min_score / max_score
