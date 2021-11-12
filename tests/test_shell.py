import sys
import os
import shutil
import time
from pathlib import Path

import pexpect
import pytest


class Expect:

    def __init__(self, expected, args=None, regex=False):
        """`expected` is either string or callable with optional `args`

        Unless `regex` is enabled, the `expected` string is matched as-is (raw).

        """
        self._expected = expected
        self._args = args
        self._regex = regex

    def __call__(self, p):
        if callable(self._expected):
            expected = self._expected(*self._args)
        else:
            expected = self._expected
        if self._regex:
            p.expect(expected)
        else:
            p.expect_exact(expected)
        assert p.before.strip('\r\n') == ''

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._expected)


class ExpectPasswordOptions:

    def __init__(self):
        self._options = {}

    def __call__(self, p):
        p.expect(10 * "([0-9]): (\\S{16})   ([a-j]): (\\S+)\r\n")
        assert p.before.strip('\r\n') == ''
        groups = p.match.groups()
        assert len(groups) == 40
        self._options = {shortcut: password
                         for shortcut, password
                         in zip(groups[::2], groups[1::2])}
        assert len(self._options) == 20

    def option(self, shortcut):
        assert shortcut in self._options
        return self._options[shortcut]


class Send:

    def __init__(self, text):
        self._text = text

    def __call__(self, p):
        p.write(self._text)
        p.flush()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._text)


class SendControl:

    def __init__(self, char):
        self._char = char

    def __call__(self, p):
        p.sendcontrol(self._char)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._char)


class Wait:

    def __init__(self, seconds):
        self._seconds = seconds

    def __call__(self, p, **kwargs):
        time.sleep(self._seconds)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._seconds)


config_file = '/tmp/test_keybox.conf'
filename = '/tmp/test_keybox.safe'
passphrase = 'secret'
dummy_filename = Path(__file__).parent / "dummy_keybox.safe"
dummy_passphrase = "test123"
expect_password_options = ExpectPasswordOptions()


@pytest.fixture()
def spawn_shell():
    if os.environ.get('COVERAGE'):
        exe = "coverage"
        args = ["run", "--parallel-mode"]
    else:
        exe = sys.executable
        args = []
    p = pexpect.spawn(exe, args + [
                      "-m", "keybox", "shell", "-c", config_file, "-f", filename,
                      '--timeout', '1'],
                      echo=False, timeout=2, encoding='utf8')
    yield p
    p.close(force=True)


@pytest.fixture
def no_keybox_file():
    assert not os.path.exists(filename)
    yield
    os.unlink(filename)


@pytest.fixture
def dummy_keybox_file():
    shutil.copyfile(dummy_filename, filename)
    yield
    os.unlink(filename)


def run_script(p, script):
    # Use copy of script, let original script unmodified
    for ln, cmd in enumerate(script):
        print("[%d] %r" % (ln, cmd))
        cmd(p)
    time.sleep(0.1)
    assert not p.isalive()


@pytest.mark.usefixtures("no_keybox_file")
def test_shell(spawn_shell):
    temp_pass = 'temporary_password'
    run_script(spawn_shell, [
        # Initialize
        Expect(f"Loading config {config_file!r}..."),
        Expect(f"Opening file {filename!r}... Not found."),
        Expect("Create new keybox file? [Y/n] "),
        Send("y\n"),
        Expect("Enter new passphrase: "),
        Send(temp_pass + "\n"),
        Expect("Re-enter new passphrase: "),
        Send(temp_pass + "\n"),
        # Shell completer
        Expect("> "),  # line 8
        Send("\t\t"),
        Expect("((add|check|copy|count|delete|export|help|import|list|modify|nowrite|"
               "print|quit|reset|select|write)\\s+){16}", regex=True),
        Send("m\t \t\t"),
        Expect("mtime     note      password  site      tags      url       "
               "user"),
        Send("pa\t \tblah\n"),
        Expect("No record selected. See `help select`."),
        # Add command
        Expect("> "),  # line 15
        Send("add\n"),
        Expect("User:     "),
        Send("\t\tjackinthebox\n"),
        Expect("Password: "),
        Send("\t\t"),
        expect_password_options,
        Expect("Password: "),
        Send("6\t\n"),
        Expect("Site:     "),
        Send("\t\tExample\n"),
        Expect("URL:      "),
        Send("http://example.com/\n"),
        Expect("Tags:     "),
        Send("web test\n"),
        Expect("Note:     "),
        Send("\n"),
        # List
        Expect("> "),  # line 32
        Send("l\n"),
        Expect("Example  jackinthebox  http://example.com/  web test  "
               "%s \\d{2}:\\d{2}:\\d{2}    \r\n" % time.strftime("%F"),
               regex=True),
        # Count
        Expect("> "),  # line 35
        Send("count\n"),
        Expect("1"),
        # Write
        Expect("> "),
        Send("w\n"),
        Expect(f"Changes saved to file {filename!r}."),
        # Select
        Expect("> "),
        Send("s\n"),
        Expect("Example  jackinthebox  http://example.com/  web test  "
               "%s \\d{2}:\\d{2}:\\d{2}    \r\n" % time.strftime("%F"),
               regex=True),
        # Print
        Expect("> "),
        Send("p\n"),
        Expect(expect_password_options.option, "6"),
        # Reset
        Expect("> "),
        Send("reset\n"),
        Expect("Enter current passphrase: "),
        Send(temp_pass + "\n"),
        Expect("Enter new passphrase: "),
        Send(passphrase + "\n"),
        Expect("Re-enter new passphrase: "),
        Send(passphrase + "\n"),
        # Is the password still okay after re-encryption?
        Expect("> "),
        Send("p\n"),
        Expect(expect_password_options.option, "6"),
        # Check
        Expect("> "),
        Send("ch\n"),
        # Delete
        Expect("> "),
        Send("d\n"),
        Expect("Delete selected record? This cannot be taken back! [y/n] "),
        Send("y\n"),
        Expect("Record deleted."),
        # Finish
        Expect("> "),
        SendControl("c"),
        Expect("quit"),
        Expect(f"Changes saved to file {filename!r}."),
    ])


@pytest.mark.usefixtures("dummy_keybox_file")
def test_timeout(spawn_shell):
    run_script(spawn_shell, [
        # Initialize
        Expect(f"Loading config {config_file!r}..."),
        Expect(f"Opening file {filename!r}... "),
        Expect("Passphrase: "),
        Send(dummy_passphrase + "\n"),
        # Finish
        Expect("> "),
        Wait(1.1),
        Expect("quit\r\nTimeout after 1 seconds."),
    ])
