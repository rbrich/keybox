import unittest
import time
import os

from pwlockr.gpg import encrypt, decrypt
from pwlockr.record import Record, COLUMNS
from pwlockr.locker import Locker, LockerRecord
from pwlockr.fileformat import format_file, parse_file
from pwlockr.ui import BaseUI
from pwlockr.pwgen import load_wordlist, pwgen


class TestPwGen(unittest.TestCase):

    def test_wordlist(self):
        words = load_wordlist()
        for word in words:
            self.assertIsInstance(word, str)
            self.assertTrue(len(word) > 0)

    def test_pwgen(self):
        pw = pwgen(num_words=0, min_length=100)
        self.assertIsInstance(pw, str)
        self.assertTrue(len(pw) == 100)
        # It should be save to expect all the symbol groups to be present
        self.assertTrue(any(c.islower() for c in pw), "At least one lowercase")
        self.assertTrue(any(c.isupper() for c in pw), "At least one uppercase")
        self.assertTrue(any(c.isdigit() for c in pw), "At least one digit")
        self.assertTrue(any(c.isprintable() and not c.isalnum() for c in pw),
                        "At least one punctuation character.")
        self.assertFalse(any(c.isspace() for c in pw), "No whitespace")
        pw = pwgen(num_words=4, min_length=50, sep=' ')
        self.assertTrue(len(pw) >= 50)
        self.assertTrue(any(c.isprintable() for c in pw))
        self.assertTrue(pw.count(' ') == 3, "Separator count")


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


class TestLockerRecord(unittest.TestCase):

    def test_mtime(self):
        locker = Locker('/tmp/x')
        record = LockerRecord(locker, Record())
        self.assertIsNotNone(record['mtime'])
        mtime_before = record['mtime']
        time.sleep(1)
        record['site'] = 'Site'
        self.assertNotEqual(mtime_before, record['mtime'])


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


class TestLocker(unittest.TestCase):

    def setUp(self):
        self._sample = {
            'site': 'Example',
            'user': 'johny',
            'url': 'http://example.com/',
            'tags': 'web test',
            'note': 'This is example record.',
            'password': 'pa$$w0rD',
        }
        self._filename = '/tmp/test_pwlockr.gpg'
        self._passphrase = 'secret'

    def test_write_read(self):
        # Write
        locker = Locker(self._filename, self._passphrase)
        for i in range(128):
            record = locker.add_record(**self._sample)
            record['site'] += str(i)
        locker.write()
        del locker
        # Read
        locker = Locker(self._filename, self._passphrase)
        locker.read()
        record = list(locker)[10]
        self.assertTrue(record['mtime'])
        self.assertEqual(record['site'], self._sample['site'] + '10')
        for key in set(self._sample.keys()) - {'site'}:
            self.assertEqual(record[key], self._sample[key])
        # Actual password is encrypted
        self.assertNotEqual(record._record['password'],
                            self._sample['password'])
        os.unlink(self._filename)


class TestUI(unittest.TestCase):

    def setUp(self):
        self._filename = '/tmp/test_pwlockr.gpg'
        self._passphrase = 'secret'
        self._passphrase_b = 'newPASS'
        self._script = [
            # open
            ("Opening file %r... " % self._filename, None),
            ("Not found. Create? [y/n] ", 'y'),
            ("Enter passphrase: ", self._passphrase),
            ("Re-enter passphrase: ", self._passphrase),
            # add
            ("User:     ", 'jackinthebox'),
            ("Password: ", 'pa$$w0rD'),
            ("Site:     ", 'Example'),
            ("URL:      ", 'http://example.com/'),
            ("Tags:     ", 'web test'),
            ("Note:     ", ''),
            # list
            ("Example  jackinthebox  http://example.com/", None),
            # count
            ("1", None),
            # select
            ("Example  jackoutofbox  http://example.com/", None),
            # print
            ("pa$$w0rD", None),
            # reset
            ("Enter current passphrase: ", self._passphrase),
            ("Enter new passphrase: ", self._passphrase_b),
            ("Re-enter new passphrase: ", self._passphrase_b),
            # print
            ("pa$$w0rD", None),
            # delete
            ("Delete selected record? This cannot be taken back! [y/n] ", "y"),
            ("Record deleted.", None),
            (0, 0),
        ]

    def test_ui(self):
        ui = BaseUI(self._filename)
        # Install hooks
        ui._input = self._check_script
        ui._input_pass = self._check_script
        ui._print = self._check_script
        # Simulate usage
        self.assertTrue(ui.open())
        ui.cmd_add()
        ui.cmd_list()
        ui.cmd_count()
        ui.cmd_modify('user', 'jackoutofbox')
        ui.cmd_select('Example')
        ui.cmd_print()
        ui.cmd_reset()
        ui.cmd_print()
        ui.cmd_delete()

    def _check_script(self, text, *_):
        expected, answer = self._script.pop(0)
        if not expected:
            raise AssertionError("No output expected, got %r." % text)
        self.assertEqual(str(text)[:40], expected[:40])
        return answer

