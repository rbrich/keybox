# BaseUI
# (open/close, basic commands)
#

from pathlib import Path
from functools import wraps
from collections import Counter
import itertools
import sys

from prompt_toolkit import prompt as prompt_input
from prompt_toolkit.formatted_text import FormattedText
from blessed import Terminal
import pyperclip

from .backend import lock_file
from .keybox import Keybox, KeyboxRecord
from .stringutil import contains
from .editor import InlineEditor
from .record import COLUMNS

DATA_DIR = Path('~/.keybox')
DEFAULT_FILENAME = 'keybox.safe'


def with_write_access(func):
    """Write access required. Decorator for UI commands."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.readonly():
            func(self, *args, **kwargs)
        else:
            print("Read-only mode.")
    return wrapper


def with_selected_record(func):
    """Require selected record. Decorator for UI commands."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._selected_record:
            func(self, *args, **kwargs)
        else:
            print("No record selected. See `help select`.")
    return wrapper


class BaseUI:

    #################
    # Other Utility #
    #################

    def _copy(self, text):
        """Wraps copy-to-clipboard function to allow overriding."""
        pyperclip.copy(text)

    def _input(self, prompt):
        """Wraps input function to allow overriding."""
        return input(prompt)

    def _input_pass(self, prompt):
        """Wraps getpass function to allow overriding."""
        return prompt_input(FormattedText([('bold', prompt)]), is_password=True)

    def _ask_yesno(self, prompt) -> bool:
        """Ask `prompt` [Y/n], return answer as bool"""
        ans = self._input(prompt + " [Y/n] ")
        return len(ans) == 0 or ans.lower()[0] == 'y'


class KeyboxUI(BaseUI):

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
        self._filename_tmp = self._filename.with_suffix(self._filename.suffix + '.tmp')
        self._wfile = None
        self._keybox = Keybox()
        self._selected_record = None  # Record

    def __del__(self):
        if self._wfile is not None:
            self._close_tmp()

    @property
    def keybox(self):
        return self._keybox

    @property
    def selected(self):
        return self._selected_record

    ################
    # Open / Close #
    ################

    def open(self, readonly=False):
        self._expand_filename()
        print("Opening file %r... " % str(self._filename), end='')
        if self._filename.exists():
            print()
            ok = self._open_existing()
            if ok and (readonly or not self._open_tmp()):
                print("Open in read-only mode.")
        else:
            print("Not found.")
            if readonly:
                return False
            ok = self._create_new()
            if ok and not self._open_tmp():
                return False
        return ok

    def close(self, write=True, ask_write=None):
        if self.readonly():
            assert not self._keybox.modified(), "Modified in read-only mode"
            return
        if self._keybox.modified() and write:
            if ask_write is None or self._ask_yesno(ask_write):
                self._write()
            return
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
            print('Not accepted.')
            return
        passphrase = self._input_pass('Enter new passphrase: ')
        passphrase_check = self._input_pass('Re-enter new passphrase: ')
        if passphrase != passphrase_check:
            print("Not same...")
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
            return print("Unknown `order_by` column:", order_by)
        order_by = candidates[0]
        try:
            columns, text = self._parse_filter(filter_expr, ('tags',))
        except ValueError as e:
            return print(e)
        for record in sorted(self._keybox, key=lambda r: r[order_by]):
            if any(contains(record[column], text) for column in columns):
                print(record)

    def cmd_select(self, filter_expr=None):
        """Select a record or print currently selected record

        Prints selected record when called without argument.
        When called with one argument, it is used as filter expression
        to search for records.

        Format of `filter_expr` is [<column>:]<text>.
        By default, columns 'site' and 'url' are searched.

        """
        if filter_expr is None:
            print(self._selected_record or "Nothing selected.")
            return
        try:
            columns, text = self._parse_filter(filter_expr, ('site', 'url'))
        except ValueError as e:
            return print(e)
        filtered_records = [record for record in self._keybox
                            if any(contains(record[column], text)
                                   for column in columns)]
        if len(filtered_records) == 0:
            print('Not found.')
            self._selected_record = None
            return
        if len(filtered_records) == 1:
            self._selected_record = filtered_records[0]
            print(self._selected_record)
            return
        filtered_records.sort(key=lambda r: r['site'])
        for n, record in enumerate(filtered_records, 1):
            print("[%d]" % n, record)
        try:
            num = int(self._input('Select: ')) - 1
            self._selected_record = filtered_records[num]
        except (ValueError, IndexError):
            print("Not found.")

    def cmd_count(self, group_by=None, min_count=2):
        """Print number of unique values in `group_by` column

        With no arguments, prints total number of records.
        With one argument, prints all values with repeated use
        (e.g. reused passwords).

        """
        try:
            min_count = int(min_count)
        except ValueError:
            return print("Invalid value for `min_count`:", min_count)
        # Total count
        if not group_by:
            return print(len(self._keybox))
        # Prepare counter objects according to `group_by` parameter
        candidates = self._keybox.get_columns(group_by)
        if len(candidates) != 1:
            return print("Unknown group_by column:", group_by)
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
                print(key.ljust(32), count, sep='')

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
        print(self._selected_record['password'])

    @with_selected_record
    def cmd_copy(self):
        """Copy password from selected record"""
        self._copy(self._selected_record['password'])

    @with_write_access
    @with_selected_record
    def cmd_modify(self, column, value=None):
        """Modify selected record

        When no `value` given, delete current value or enter multi-line editor
        (in case of password).

        """
        candidates = self._keybox.get_columns(column)
        if len(candidates) != 1:
            return print('Unknown column:', column)
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
        print("Record deleted.")

    def cmd_export(self, filename='-', file_format='plain'):
        """Export all records to a plain-text or JSON file.

        The output file will contain decrypted passwords!

        """
        if filename == '-':
            self._keybox.export_file(sys.stdout, file_format)
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                self._keybox.export_file(f, file_format)

    def cmd_import(self, filename='-', file_format='keybox_gpg', quiet=False):
        """Import non-identical records from another keybox"""

        class PassphraseCanceled(Exception):
            pass

        def passphrase_cb():
            try:
                return self._input_pass("Passphrase: ")
            except (KeyboardInterrupt, EOFError):
                print()
                raise PassphraseCanceled()

        def diff_columns(rec1, rec2):
            for column in COLUMNS:
                if rec1.get(column) != rec2.get(column):
                    yield column

        term = Terminal()

        def highlight(text, condition):
            return term.bright_yellow(text) if condition else term.yellow(text)

        def format_rec(rec, diff_cols=()):
            return ', '.join(
                f'{column}={highlight(repr(rec[column]), column in diff_cols)}'
                for column in rec.get_columns())

        def resolve_cb(local_recs, new_rec):
            print(term.bright_blue("Updating:"))
            all_diff_cols = set()
            for n, rec in enumerate(local_recs):
                diff_cols = set(diff_columns(rec, new_rec))
                all_diff_cols.update(diff_cols)
                print(term.bold('[%s] local:   ') % n, format_rec(rec, diff_cols))
            print(term.bold('[*] incoming:'), format_rec(new_rec, all_diff_cols))
            while True:
                ans = self._input("Replace local [%s] / Add incoming as new [a] / Keep local [k]: "
                                  % ']['.join(str(n) for n
                                              in range(len(local_recs))))
                if ans == 'a':
                    return None, 'add'
                if ans == 'k':
                    return None, 'keep_local'
                try:
                    n = int(ans)
                    if n < 0 or n >= len(local_recs):
                        continue
                    return local_recs[n], 'replace'
                except ValueError:
                    continue

        def print_new_cb(rec):
            if not quiet:
                print(term.bright_green("Adding:      "), format_rec(rec))

        def do_import(file):
            n_total, n_new, n_updated = self._keybox.import_file(
                file, file_format, passphrase_cb, resolve_cb, print_new_cb)
            print("checked %d records (%d new, %d updated, %d identical)"
                  % (n_total, n_new, n_updated, n_total - n_new - n_updated))

        print("Opening input file %r... " % filename)
        try:
            if filename == '-':
                do_import(sys.stdin.buffer)
            else:
                with open(filename, 'rb') as f:
                    do_import(f)
            return True
        except PassphraseCanceled:
            return False

    ################
    # File Utility #
    ################

    @staticmethod
    def get_default_filename():
        return DATA_DIR / DEFAULT_FILENAME

    def _expand_filename(self):
        self._filename = self._filename.expanduser()
        self._filename_tmp = self._filename.with_suffix(self._filename.suffix + '.tmp')

    def _open_existing(self):
        try:
            with open(self._filename, 'rb') as f:
                try:
                    self._keybox.read(f, lambda: self._input_pass("Passphrase: "))
                except (KeyboardInterrupt, EOFError):  # thrown from _input_pass
                    print()
                    return False
        except IOError as e:
            print(e)
            return False
        return True

    def _create_new(self, ask=True):
        if not ask or self._ask_yesno("Create new keybox file?"):
            passphrase = self._input_pass("Enter new passphrase: ")
            passphrase_check = self._input_pass("Re-enter new passphrase: ")
            if passphrase != passphrase_check:
                print("Not same...")
                return False
            self._keybox.set_passphrase(passphrase)
        else:  # answer = no
            return False
        return True

    def _open_tmp(self):
        """Prepare tmp file for writing and lock it"""
        try:
            dirname = self._filename_tmp.parent
            if dirname.name == '.keybox':
                dirname.mkdir(0o700, exist_ok=True)
            # Open tmp file for writing. It may exist, if:
            # * another process has opened the keybox (handled by lock_file below)
            # * it remained in place after unclean exit of another process (overwrite it silently)
            self._wfile = self._filename_tmp.open('wb')
        except OSError as e:
            print("Warning: Can't open file for writing: %s" % e)
            return False
        try:
            lock_file(self._wfile)
            return True
        except OSError:
            self._close_tmp(unlink=False)
            print("Warning: File locked by another process.")
            return False

    def _close_tmp(self, unlink=True):
        """Close tmp file (this also releases the lock)"""
        self._wfile.close()
        self._wfile = None
        if unlink:
            self._filename_tmp.unlink()

    def _write(self):
        # Write records to tmp file
        self._keybox.write(self._wfile)
        if sys.platform == "win32":
            self._close_tmp(unlink=False)
        # Then rename it to target name, potentially overwriting old version
        self._filename_tmp.replace(self._filename)
        # Close tmp file, which will also release the lock
        # It's important to do this after rename to avoid race condition
        # (Windows: can't rename the file before closing)
        if sys.platform != "win32":
            self._close_tmp(unlink=False)
        print(f"Changes saved to file {str(self._filename)!r}.")

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
                raise ValueError("Unknown or ambiguous column name: " + column)
            selected_columns += candidates
        if text == '*':
            text = ''
        return selected_columns, text
