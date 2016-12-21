# BaseUI
# (open/close, basic commands)
#

from getpass import getpass
from functools import wraps
from collections import Counter
import itertools
import os.path
import fcntl
import sys

from keybox.keybox import Keybox, KeyboxRecord
from keybox.stringutil import contains
from keybox.editor import InlineEditor

DATA_DIR = '~/.keybox'
DEFAULT_FILENAME = 'keybox.gpg'


def with_write_access(func):
    """Write access required. Decorator for UI commands."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.readonly():
            func(self, *args, **kwargs)
        else:
            self._print("Read-only mode.")
    return wrapper


def with_selected_record(func):
    """Require selected record. Decorator for UI commands."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._selected_record:
            func(self, *args, **kwargs)
        else:
            self._print("No record selected. See `help select`.")
    return wrapper


class BaseUI:

    """UI base commands.

    `open` MUST be called before any other method and it MUST return success.
    `close` should be called before releasing the object but ONLY when `open`
    was successful.

    Other methods are usable only after successful `open`.
    There is no internal check for this and results of not honoring
    this procedure would be potentially disastrous.

    """

    def __init__(self, filename=None):
        self._filename = filename or self.get_default_filename()
        #: We will write to temporary file to avoid data loss when write fails
        #: When write succeeds, the temp file will be moved to target file name
        self._filename_tmp = self._filename + '.tmp'
        self._wfile = None
        self._keybox = Keybox()
        self._selected_record = None  # Record

    @property
    def selected(self):
        return self._selected_record

    ################
    # Open / Close #
    ################

    def open(self, readonly=False):
        self._expand_filename()
        self._print("Opening file %r... " % self._filename, end='')
        if os.path.exists(self._filename):
            print()
            ok = self._open_existing()
            if ok and (readonly or not self._open_tmp()):
                self._print("Open in read-only mode.")
        else:
            print("Not found.")
            if readonly:
                return False
            ok = self._create_new()
            if ok and not self._open_tmp():
                return False
        return ok

    def close(self, write=True):
        if self.readonly():
            assert not self._keybox.modified(), "Modified in read-only mode"
            return
        if self._keybox.modified() and write:
            self._write()
        else:
            self._close_tmp()

    def readonly(self):
        return self._wfile is None

    ###############
    # UI Commands #
    ###############

    @with_write_access
    def cmd_write(self):
        """Write changes to keybox file"""
        if self._keybox.modified():
            self._write()
            self._open_tmp()

    @with_write_access
    def cmd_reset(self):
        """Change master passphrase"""
        passphrase = self._input_pass('Enter current passphrase: ')
        if not self._keybox.check_passphrase(passphrase):
            self._print('Not accepted.')
            return
        passphrase = self._input_pass('Enter new passphrase: ')
        passphrase_check = self._input_pass('Re-enter new passphrase: ')
        if passphrase != passphrase_check:
            self._print("Not same...")
            return
        self._keybox.set_passphrase(passphrase)

    @with_write_access
    def cmd_add(self, user=None, password=None):
        """Add new record

        Selects the new record when done.

        """
        record = {
            'user':     user or self._input('User:'.ljust(10)),
            'password': password or self._input('Password:'.ljust(10)),
            'site':     self._input('Site:'.ljust(10)),
            'url':      self._input('URL:'.ljust(10)),
            'tags':     self._input('Tags:'.ljust(10)),
            'note':     self._input('Note:'.ljust(10)),
        }
        self._selected_record = self._keybox.add_record(**record)

    def cmd_list(self, filter_expr='', order_by='site'):
        """Print list of records, applying filters

        Format of `filter_expr` is [<column>:]<text>. Default column is 'tags'.
        Special expression '*' matches everything.

        Select column for ordering using second parameter `order_by`.
        Default is `site`.

        Examples:

        * ``list * mtime`` (list everything, ordered by last modification time)
        * ``list shop`` (list records with "shop" tag)
        * ``list user:admin url`` (records with "admin" user, ordered by URL)

        """
        candidates = self._keybox.get_columns(order_by)
        if len(candidates) != 1:
            return self._print("Unknown `order_by` column:", order_by)
        order_by = candidates[0]
        try:
            columns, text = self._parse_filter(filter_expr, ('tags',))
        except Exception as e:
            return self._print(e)
        for record in sorted(self._keybox, key=lambda r: r[order_by]):
            if any(contains(record[column], text) for column in columns):
                self._print(record)

    def cmd_select(self, filter_expr=None):
        """Select a record or print currently selected record

        Prints selected record when called without argument.
        When called with one argument, it is used as filter expression
        to search for records.

        Format of `filter_expr` is [<column>:]<text>.
        By default, columns 'site' and 'url' are searched.

        """
        if filter_expr is None:
            self._print(self._selected_record or "Nothing selected.")
            return
        try:
            columns, text = self._parse_filter(filter_expr, ('site', 'url'))
        except Exception as e:
            return self._print(e)
        filtered_records = [record for record in self._keybox
                            if any(contains(record[column], text)
                                   for column in columns)]
        if len(filtered_records) == 0:
            self._print('Not found.')
            self._selected_record = None
            return
        if len(filtered_records) == 1:
            self._selected_record = filtered_records[0]
            self._print(self._selected_record)
            return
        filtered_records.sort(key=lambda r: r['site'])
        for n, record in enumerate(filtered_records, 1):
            self._print("[%d]" % n, record)
        try:
            num = int(self._input('Select: ')) - 1
            self._selected_record = filtered_records[num]
        except (ValueError, IndexError):
            self._print("Not found.")

    def cmd_count(self, group_by=None, min_count=2):
        """Print number of unique values in `group_by` column

        With no arguments, prints total number of records.
        With one argument, prints all values with repeated use
        (e.g. reused passwords).

        """
        try:
            min_count = int(min_count)
        except ValueError:
            return self._print("Invalid value for `min_count`:", min_count)
        # Total count
        if not group_by:
            return self._print(len(self._keybox))
        # Prepare counter objects according to `group_by` parameter
        candidates = self._keybox.get_columns(group_by)
        if len(candidates) != 1:
            return self._print("Unknown group_by column:", group_by)
        if 'tag'.startswith(group_by.lower()):
            counter = Counter(itertools.chain.from_iterable(
                record['tags'].split() for record in self._keybox))
        else:
            counter = Counter(record[candidates[0]] for record in self._keybox)
        # Print the counts
        for key, count in counter.most_common():
            if count < min_count:
                break
            # Skip empty values
            if key:
                self._print(key.ljust(32), count, sep='')

    def cmd_check(self):
        """Check consistency of records

        Each record is decrypted to check if the encryption is valid.

        """
        for raw_record in self._keybox.raw_records:
            record = KeyboxRecord(self._keybox, raw_record)
            if not raw_record['password']:
                print("Warning: Empty passphrase:")
                print(record)

    @with_selected_record
    def cmd_print(self):
        """Print password from selected record"""
        self._print(self._selected_record['password'])

    @with_write_access
    @with_selected_record
    def cmd_modify(self, column, value=None):
        """Modify selected record

        When no `value` given, delete current value or enter multi-line editor
        (in case of password).

        """
        candidates = self._keybox.get_columns(column)
        if len(candidates) != 1:
            return self._print('Unknown column:', column)
        column = candidates[0]
        if column == "password" and value is None:
            # Multi-line editor
            print("[F10/Escape] Finish  [Ctrl-C] Cancel")
            value = InlineEditor().edit(self._selected_record[column])
        self._selected_record[column] = value

    @with_write_access
    @with_selected_record
    def cmd_delete(self):
        """Delete selected record"""
        ans = self._input("Delete selected record? "
                          "This cannot be taken back! [y/n] ")
        if ans != 'y':
            return
        self._keybox.delete_record(self._selected_record)
        self._selected_record = None
        self._print("Record deleted.")

    ################
    # File Utility #
    ################

    @staticmethod
    def get_default_filename():
        return os.path.join(DATA_DIR, DEFAULT_FILENAME)

    def _expand_filename(self):
        self._filename = os.path.expanduser(self._filename)
        self._filename_tmp = self._filename + '.tmp'

    def _open_existing(self):
        try:
            passphrase = self._input_pass("Passphrase: ")
        except (KeyboardInterrupt, EOFError):
            self._print()
            return False
        try:
            self._keybox.set_passphrase(passphrase)
            with open(self._filename, 'rb') as f:
                self._keybox.read(f)
        except IOError as e:
            self._print(e)
            return False
        return True

    def _create_new(self):
        ans = self._input("Create new keybox file? [Y/n] ")
        if len(ans) == 0 or ans.lower()[0] == 'y':
            passphrase = self._input_pass("Enter passphrase: ")
            passphrase_check = self._input_pass("Re-enter passphrase: ")
            if passphrase != passphrase_check:
                self._print("Not same...")
                return False
            self._keybox.set_passphrase(passphrase)
        else:  # ans != 'y'
            return False
        return True

    def _open_tmp(self):
        """Prepare tmp file for writing and lock it"""
        try:
            dirname = os.path.dirname(self._filename_tmp)
            if dirname.endswith('/.keybox'):
                os.makedirs(dirname, 0o700, exist_ok=True)
            self._wfile = open(self._filename_tmp, 'wb')
        except OSError as e:
            self._print("Warning: Can't open file for writing: %s" % e)
            return False
        try:
            fcntl.lockf(self._wfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self._close_tmp()
            self._print("Warning: File locked by another process.")
            return False

    def _close_tmp(self, unlink=True):
        """Close tmp file (this also releases the lock)"""
        self._wfile.close()
        self._wfile = None
        if unlink:
            os.unlink(self._filename_tmp)

    def _write(self):
        # Write records to tmp file
        self._keybox.write(self._wfile)
        # Then rename it to target name, potentially overwriting old version
        os.rename(self._filename_tmp, self._filename)
        # Close tmp file, which will also release the lock
        # It's important to do this after rename to avoid race condition
        self._close_tmp(unlink=False)
        self._print("Changes saved to %s." % self._filename)

    #################
    # Other Utility #
    #################

    def _parse_filter(self, filter_expr, default_columns: tuple) -> tuple:
        """Parse filter expression, check column names.

        Returns tuple: ((column1, ...), text).

        """
        try:
            columns, text = filter_expr.split(':', 1)
            columns = columns.split(',')
        except ValueError:
            columns = default_columns
            text = filter_expr
        selected_columns = []
        for column in columns:
            candidates = self._keybox.get_columns(column)
            if len(candidates) != 1:
                raise Exception("Unknown or ambiguous column name: " + column)
            selected_columns += candidates
        if text == '*':
            text = ''
        return selected_columns, text

    def _print(self, *args, **kwargs):
        """Wrap print function to allow overriding."""
        print(*args, **kwargs)
        sys.stdout.flush()

    def _input(self, prompt):
        """Wrap input function to allow overriding."""
        return input(prompt)

    def _input_pass(self, prompt):
        """Wrap getpass function to allow overriding."""
        return getpass(prompt)
