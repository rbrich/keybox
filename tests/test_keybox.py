import pytest
from io import StringIO, BytesIO
from pathlib import Path

from keybox.envelope import Envelope
from keybox.record import Record, COLUMNS
from keybox.keybox import Keybox, KeyboxRecord
from keybox.fileformat import format_file, parse_file
from keybox import pwgen

dummy_filename = Path(__file__).parent / "dummy_keybox.safe"
dummy_passphrase = "test123"
dummy_plain = """site	user	url	tags	mtime	note	password
test	test	http://test.test	test	2021-11-06 20:23:59	test!	test
"""
dummy_json = '[{"site": "test", "user": "test", "url": "http://test.test", "tags": "test", ' \
             '"mtime": "2021-11-06 20:23:59", "note": "test!", "password": "test"}]'

# modified 4 fields of existing record, and added a new record
dummy_plain_update = """site	user	url	tags	mtime	note	password
test	mona	http://test.test	test	2021-11-12 20:27:03	updated	test123
second	lisa	https://example.com	tag2	2021-11-12 20:28:12	new one	secret
"""


class TestPasswordGenerator:

    def test_wordlist(self):
        words = pwgen.load_wordlist()
        for word in words:
            assert isinstance(word, str)
            assert len(word) > 0

    def test_generate_passphrase(self):
        pw = pwgen.generate_passphrase(num_upper=1, num_digits=1, num_special=1)
        assert isinstance(pw, str)
        assert len(pw) >= pwgen.MIN_LENGTH
        assert any(c.islower() for c in pw), "At least one lowercase"
        assert any(c.isupper() for c in pw), "At least one uppercase"
        assert any(c.isdigit() for c in pw), "At least one digit"
        assert any(c.isprintable() and not c.isalnum() for c in pw), \
               "At least one punctuation character."
        assert not any(c.isspace() for c in pw), "No whitespace"
        pw = pwgen.generate_password(length=50)
        assert len(pw) == 50
        assert all(c.isprintable() for c in pw)


class TestCrypt:

    def _encrypt_decrypt(self, data, pp):
        envelope = Envelope()
        envelope.set_passphrase(pp)
        ciphertext = envelope.encrypt(data)
        plaintext = envelope.decrypt(ciphertext)
        assert data == plaintext

    def test_crypt(self):
        self._encrypt_decrypt(b'test', 'abc')

    def test_crypt_large(self):
        big_data = b''.join([b'big_data'] * 1024 ** 2)  # 8 MiB
        self._encrypt_decrypt(big_data, 'PassWord')

    def test_wrong_passphrase(self):
        data = b'test'
        env = Envelope()
        env.set_passphrase('a')
        ciphertext = env.encrypt(data)
        env = Envelope()
        env.set_passphrase('b')
        with pytest.raises(Exception):
            env.decrypt(ciphertext)


class TestRecord:

    def test_standard_columns(self):
        record = Record()
        empty_repr = "Record(site='', user='', url='', tags='', mtime='', " \
                     "note='', password='')"
        assert repr(record) == empty_repr
        assert record.get_columns() == COLUMNS

    def test_custom_columns(self):
        record = Record(a='1', b='2', columns=['a', 'b', 'c'])
        assert repr(record) == "Record(a='1', b='2', c='')"
        record['c'] = '3'
        record['d'] = '4'
        assert repr(record) == "Record(a='1', b='2', c='3', d='4')"
        assert record['a'] == '1'
        assert record['c'] == '3'

    def test_compare(self):
        record0 = Record()
        record1 = Record()
        record2 = Record()
        for record in (record1, record2):
            record['site'] = 'Site'
            record['user'] = 'johny'
            record['password'] = 'PASSWORD'
        assert record1 == record2
        assert record0 != record1
        record0['site'] = 'Site'
        record0['user'] = 'johny'
        record0['password'] = 'password'
        assert record0 != record1


class TestFormat:

    _example_record = Record({
        'site': 'Example',
        'user': 'johny',
        'url': 'http://example.com/',
        'tags': 'web test',
        'note': 'This is example record.',
        'mtime': 'now',
        'password': 'pa$$w0rD',
    })

    def test_format_parse(self):
        records = [self._example_record.copy() for _ in range(1000)]
        for n, record in enumerate(records):
            record['site'] += str(n)
        data = format_file(records)
        parsed_records, parsed_columns = parse_file(data)
        assert records == parsed_records


class TestKeyboxRecord:

    def test_mtime(self):
        keybox = Keybox()
        # Make empty record
        record = Record()
        record_proxy = KeyboxRecord(keybox, record)
        # New records are automatically touched
        assert record['mtime']
        # Cannot write mtime through proxy
        with pytest.raises(Exception):
            record_proxy['mtime'] = "sometime"
        # But still can through dumb Record
        record['mtime'] = "sometime"
        # Update something, check that mtime also updates
        record_proxy['site'] = 'Site'
        assert "sometime" != record['mtime']


class TestKeybox:

    _sample = {
        'site': 'Example',
        'user': 'johny',
        'url': 'http://example.com/',
        'tags': 'web test',
        'note': 'This is example record.',
        'password': 'pa$$w0rD',
    }
    _filename = 'test_keybox.safe'
    _passphrase = 'secret'

    def test_write_read(self, tmp_path):
        safe_file = tmp_path / self._filename
        # Write
        keybox = Keybox()
        keybox.set_passphrase(self._passphrase)
        for i in range(128):
            record = keybox.add_record(**self._sample)
            record['site'] += str(i)
        keybox[20]['tags'] = 'email'
        keybox[30]['tags'] = 'test it'
        with open(safe_file, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read
        keybox = Keybox()
        with open(safe_file, 'rb') as f:
            keybox.read(f, lambda: self._passphrase)
        record = keybox[10]
        assert record['mtime']
        assert record['site'] == self._sample['site'] + '10'
        # Check rest of fields
        for key in set(self._sample.keys()) - {'site'}:
            assert record[key] == self._sample[key]
        # Actual password is encrypted
        assert record._record['password'] != self._sample['password']
        # Tags are parsed into sorted list
        assert keybox.get_tags() == ['email', 'it', 'test', 'web']

    def test_master_password_change(self, tmp_path):
        safe_file = tmp_path / self._filename
        # Write
        keybox = Keybox()
        keybox.set_passphrase(self._passphrase)
        keybox.add_record(**self._sample)
        keybox.set_passphrase(self._passphrase + '2')
        with open(safe_file, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read
        keybox = Keybox()
        with open(safe_file, 'rb') as f:
            keybox.read(f, lambda: self._passphrase + '2')
        record = dict(keybox[0])
        del record['mtime']
        assert record == self._sample
        # Change passphrase
        keybox.set_passphrase(self._passphrase + '3')
        record = dict(keybox[0])
        del record['mtime']
        assert record == self._sample
        with open(safe_file, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read with old passphrase
        keybox = Keybox()
        with open(safe_file, 'rb') as f:
            # FIXME: custom exception for authentication error
            with pytest.raises(Exception):
                keybox.read(f, lambda: self._passphrase)
        # Read with new passphrase
        with open(safe_file, 'rb') as f:
            keybox.read(f, lambda: self._passphrase + '3')
        record = dict(keybox[0])
        del record['mtime']
        assert record == self._sample


class TestExportImport:

    def test_export(self):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        out = StringIO()
        keybox.export_file(out, 'plain')
        assert out.getvalue() == dummy_plain

        out = StringIO()
        keybox.export_file(out, 'json')
        assert out.getvalue() == dummy_json

        out = StringIO()
        with pytest.raises(NotImplementedError):
            keybox.export_file(out, 'keybox')
        with pytest.raises(NotImplementedError):
            keybox.export_file(out, 'keybox_gpg')

    def test_import_existing(self):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        assert keybox.import_file(BytesIO(dummy_plain.encode()), 'plain', None, None, None) \
            == (1, 0, 0)
        assert keybox.import_file(BytesIO(dummy_json.encode()), 'json', None, None, None) \
            == (1, 0, 0)
        assert keybox.import_file(BytesIO(b'[]'), 'json', None, None, None) \
            == (0, 0, 0)
        with open(dummy_filename, 'rb') as f:
            assert keybox.import_file(f, 'keybox', lambda: dummy_passphrase, None, None) \
                == (1, 0, 0)

        with pytest.raises(NotImplementedError):
            keybox.import_file(BytesIO(b''), 'other', None, None, None)

    def _import_new_update(self, resolution, result_tuple):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        def fn_update(matched_recs, new_rec):
            assert len(matched_recs) == 1
            assert new_rec['user'] == 'mona'
            if resolution == 'replace':
                return matched_recs[0], 'replace'
            else:
                return None, resolution

        def fn_new(rec):
            assert repr(rec) == \
                   R"Record(site='second', user='lisa', url='https://example.com', " \
                   R"tags='tag2', mtime='2021-11-12 20:28:12', note='new one', " \
                   R"password='secret')"

        assert keybox.import_file(BytesIO(dummy_plain_update.encode()), 'plain',
                                  None, fn_update, fn_new) == \
               result_tuple

    def test_import_new_update(self):
        # result_tuple = (n_imported, n_new, n_updated)
        self._import_new_update('replace', (2, 1, 1))
        self._import_new_update('add', (2, 2, 0))
        self._import_new_update('keep_local', (2, 1, 0))
        with pytest.raises(ValueError):
            self._import_new_update('whatever', None)
