import unittest
import os

from keybox.gpg import encrypt, decrypt
from keybox.record import Record, COLUMNS
from keybox.keybox import Keybox, KeyboxRecord
from keybox.fileformat import format_file, parse_file
from keybox import pwgen


class TestPasswordGenerator(unittest.TestCase):

    def test_wordlist(self):
        words = pwgen.load_wordlist()
        for word in words:
            self.assertIsInstance(word, str)
            self.assertTrue(len(word) > 0)

    def test_generate_passphrase(self):
        pw = pwgen.generate_passphrase()
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
        encdata = encrypt(data, pp)
        decdata = decrypt(encdata, pp)
        self.assertEqual(data, decdata)

    def test_crypt(self):
        self._encrypt_decrypt(b'test', 'abc')

    def test_crypt_large(self):
        big_data = b''.join([b'big_data'] * 1024 ** 2)  # 8 MiB
        self._encrypt_decrypt(big_data, 'PassWord')

    def test_wrong_passphrase(self):
        data = b'test'
        encdata = encrypt(data, 'a')
        self.assertRaises(Exception, decrypt, encdata, 'b')


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
        keybox = Keybox('/tmp/x')
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
        self._filename = '/tmp/test_keybox.gpg'
        self._passphrase = 'secret'

    def test_write_read(self):
        # Write
        keybox = Keybox(self._passphrase)
        for i in range(128):
            record = keybox.add_record(**self._sample)
            record['site'] += str(i)
        keybox[20]['tags'] = 'email'
        keybox[30]['tags'] = 'test it'
        with open(self._filename, 'wb') as f:
            keybox.write(f)
        del keybox
        # Read
        keybox = Keybox(self._passphrase)
        with open(self._filename, 'rb') as f:
            keybox.read(f)
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
