import unittest
import os
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


class TestPasswordGenerator(unittest.TestCase):

    def test_wordlist(self):
        words = pwgen.load_wordlist()
        for word in words:
            self.assertIsInstance(word, str)
            self.assertTrue(len(word) > 0)

    def test_generate_passphrase(self):
        pw = pwgen.generate_passphrase(num_upper=1, num_digits=1, num_special=1)
        self.assertIsInstance(pw, str)
        self.assertTrue(len(pw) >= pwgen.MIN_LENGTH)
        self.assertTrue(any(c.islower() for c in pw), "At least one lowercase")
        self.assertTrue(any(c.isupper() for c in pw), "At least one uppercase")
        self.assertTrue(any(c.isdigit() for c in pw), "At least one digit")
        self.assertTrue(any(c.isprintable() and not c.isalnum() for c in pw),
                        "At least one punctuation character.")
        self.assertFalse(any(c.isspace() for c in pw), "No whitespace")
        pw = pwgen.generate_password(length=50)
        self.assertTrue(len(pw) == 50)
        self.assertTrue(all(c.isprintable() for c in pw))


class TestCrypt(unittest.TestCase):

    def _encrypt_decrypt(self, data, pp):
        envelope = Envelope()
        envelope.set_passphrase(pp)
        encdata = envelope.encrypt(data)
        decdata = envelope.decrypt(encdata)
        self.assertEqual(data, decdata)

    def test_crypt(self):
        self._encrypt_decrypt(b'test', 'abc')

    def test_crypt_large(self):
        big_data = b''.join([b'big_data'] * 1024 ** 2)  # 8 MiB
        self._encrypt_decrypt(big_data, 'PassWord')

    def test_wrong_passphrase(self):
        data = b'test'
        env1 = Envelope()
        env1.set_passphrase('a')
        encdata = env1.encrypt(data)
        env2 = Envelope()
        env2.set_passphrase('b')
        self.assertRaises(Exception, env2.decrypt, encdata)


class TestRecord(unittest.TestCase):

    def test_standard_columns(self):
        record = Record()
        empty_repr = "Record(site='', user='', url='', tags='', mtime='', " \
                     "note='', password='')"
        self.assertEqual(repr(record), empty_repr)
        self.assertEqual(record.get_columns(), COLUMNS)

    def test_custom_columns(self):
        record = Record(a='1', b='2', columns=['a', 'b', 'c'])
        self.assertEqual(repr(record), "Record(a='1', b='2', c='')")
        record['c'] = '3'
        record['d'] = '4'
        self.assertEqual(repr(record), "Record(a='1', b='2', c='3', d='4')")
        self.assertEqual(record['a'], '1')
        self.assertEqual(record['c'], '3')

    def test_compare(self):
        record0 = Record()
        record1 = Record()
        record2 = Record()
        for record in (record1, record2):
            record['site'] = 'Site'
            record['user'] = 'johny'
            record['password'] = 'PASSWORD'
        self.assertEqual(record1, record2)
        self.assertNotEqual(record0, record1)
        record0['site'] = 'Site'
        record0['user'] = 'johny'
        record0['password'] = 'password'
        self.assertNotEqual(record0, record1)


class TestFormat(unittest.TestCase):

    def setUp(self):
        self._example_record = Record({
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
        self.assertEqual(records, parsed_records)


class TestKeyboxRecord(unittest.TestCase):

    def test_mtime(self):
        keybox = Keybox()
        # Make empty record
        record = Record()
        record_proxy = KeyboxRecord(keybox, record)
        # New records are automatically touched
        self.assertTrue(record['mtime'])
        # Cannot write mtime through proxy
        with self.assertRaises(Exception):
            record_proxy['mtime'] = "sometime"
        # But still can through dumb Record
        record['mtime'] = "sometime"
        # Update something, check that mtime also updates
        record_proxy['site'] = 'Site'
        self.assertNotEqual("sometime", record['mtime'])


class TestKeybox(unittest.TestCase):

    def setUp(self):
        self._sample = {
            'site': 'Example',
            'user': 'johny',
            'url': 'http://example.com/',
            'tags': 'web test',
            'note': 'This is example record.',
            'password': 'pa$$w0rD',
        }
        self._filename = '/tmp/test_keybox.safe'
        self._passphrase = 'secret'

    def test_write_read(self):
        # Write
        keybox = Keybox()
        keybox.set_passphrase(self._passphrase)
        for i in range(128):
            record = keybox.add_record(**self._sample)
            record['site'] += str(i)
        keybox[20]['tags'] = 'email'
        keybox[30]['tags'] = 'test it'
        with open(self._filename, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read
        keybox = Keybox()
        with open(self._filename, 'rb') as f:
            keybox.read(f, lambda: self._passphrase)
        record = keybox[10]
        self.assertTrue(record['mtime'])
        self.assertEqual(record['site'], self._sample['site'] + '10')
        # Check rest of fields
        for key in set(self._sample.keys()) - {'site'}:
            self.assertEqual(record[key], self._sample[key])
        # Actual password is encrypted
        self.assertNotEqual(record._record['password'],
                            self._sample['password'])
        # Tags are parsed into sorted list
        self.assertEqual(keybox.get_tags(), ['email', 'it', 'test', 'web'])
        # Clean up
        os.unlink(self._filename)

    def test_master_password_change(self):
        # Write
        keybox = Keybox()
        keybox.set_passphrase(self._passphrase)
        keybox.add_record(**self._sample)
        keybox.set_passphrase(self._passphrase + '2')
        with open(self._filename, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read
        keybox = Keybox()
        with open(self._filename, 'rb') as f:
            keybox.read(f, lambda: self._passphrase + '2')
        record = dict(keybox[0])
        del record['mtime']
        self.assertEqual(record, self._sample)
        # Change passphrase
        keybox.set_passphrase(self._passphrase + '3')
        record = dict(keybox[0])
        del record['mtime']
        self.assertEqual(record, self._sample)
        with open(self._filename, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read with old passphrase
        keybox = Keybox()
        with open(self._filename, 'rb') as f:
            # FIXME: custom exception for authentication error
            self.assertRaises(Exception, keybox.read, f, lambda: self._passphrase)
        # Read with new passphrase
        with open(self._filename, 'rb') as f:
            keybox.read(f, lambda: self._passphrase + '3')
        record = dict(keybox[0])
        del record['mtime']
        self.assertEqual(record, self._sample)


class TestExportImport(unittest.TestCase):

    def test_export(self):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        out = StringIO()
        keybox.export_file(out, 'plain')
        self.assertEqual(out.getvalue(), dummy_plain)

        out = StringIO()
        keybox.export_file(out, 'json')
        self.assertEqual(out.getvalue(), dummy_json)

        out = StringIO()
        self.assertRaises(NotImplementedError, keybox.export_file, out, 'keybox')
        self.assertRaises(NotImplementedError, keybox.export_file, out, 'keybox_gpg')

    def test_import_existing(self):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        self.assertEqual(
            keybox.import_file(BytesIO(dummy_plain.encode()), 'plain', None, None, None),
            (1, 0, 0))
        self.assertEqual(
            keybox.import_file(BytesIO(dummy_json.encode()), 'json', None, None, None),
            (1, 0, 0))
        self.assertEqual(
            keybox.import_file(BytesIO(b'[]'), 'json', None, None, None),
            (0, 0, 0))
        with open(dummy_filename, 'rb') as f:
            self.assertEqual(
                keybox.import_file(f, 'keybox', lambda: dummy_passphrase, None, None),
                (1, 0, 0))

        self.assertRaises(NotImplementedError, keybox.import_file,
                          BytesIO(b''), 'other', None, None, None)

    def _import_new_update(self, resolution, result_tuple):
        keybox = Keybox()
        with open(dummy_filename, 'rb') as f:
            keybox.read(f, lambda: dummy_passphrase)

        def fn_update(matched_recs, new_rec):
            self.assertEqual(len(matched_recs), 1)
            self.assertEqual(new_rec['user'], 'mona')
            if resolution == 'replace':
                return matched_recs[0], 'replace'
            else:
                return None, resolution

        def fn_new(rec):
            self.assertEqual(repr(rec),
                             R"Record(site='second', user='lisa', url='https://example.com', "
                             R"tags='tag2', mtime='2021-11-12 20:28:12', note='new one', "
                             R"password='secret')")

        self.assertEqual(
            keybox.import_file(BytesIO(dummy_plain_update.encode()), 'plain',
                               None, fn_update, fn_new),
            result_tuple)

    def test_import_new_update(self):
        # result_tuple = (n_imported, n_new, n_updated)
        self._import_new_update('replace', (2, 1, 1))
        self._import_new_update('add', (2, 2, 0))
        self._import_new_update('keep_local', (2, 1, 0))
        self.assertRaises(AssertionError, self._import_new_update, 'unknown', None)
