import sys
import os
import re
import select
import time

import ptyprocess
import pytest


class ExpectBase:

    def __call__(self, p, *, poll, line, **kwargs):
        # Read shell output
        rest = getattr(p, '_Expect_unread', None)
        self.init()
        if rest:
            self.fill(rest)
            rest = None
        while self.more():
            events = poll.poll(2000)
            assert len(events), "Timeout while waiting for shell output, " \
                                "expected: %r (line %s)" % \
                                (self, line)
            for fd, event in events:
                assert fd == p.fileno()
                assert event & select.POLLIN
                event -= select.POLLIN
                try:
                    text = p.read()
                    if not text:
                        continue
                    rest = self.fill(text)
                except EOFError:
                    event |= select.POLLHUP
                assert not event or event == select.POLLHUP
                if event & select.POLLHUP:
                    assert not self.more(), "Expected more output from shell"
                    break
        self.check()
        p._Expect_unread = rest

    def init(self):
        """To be overriden"""

    def more(self):
        """To be overriden"""
        return False

    def fill(self, text):
        """To be overriden"""

    def check(self):
        """To be overriden"""


class Expect(ExpectBase):

    def __init__(self, expected, args=None):
        """`expected` is either string or callable with optional `args`

        The callable is evaluated in :meth:`init`.

        """
        self._expected = expected
        self._args = args
        self._got = ''

    def init(self):
        if callable(self._expected):
            self._expected = self._expected(*self._args)

    def more(self):
        return len(self._got) < len(self._expected)

    def fill(self, text):
        self._got += text.replace('\r\n', '\n')

    def check(self):
        assert str(self._expected).strip('\n') == self._got.strip('\n'), \
            "Script expected %r, got %r" % (self._expected, self._got)

    def __repr__(self):
        return "%s(expected=%r, got=%r)"\
               % (self.__class__.__name__, self._expected, self._got)


class ExpectMatch(Expect):

    def __init__(self, pattern):
        super().__init__(pattern)

    def check(self):
        m = re.match(self._expected, self._got)
        assert m is not None


class ExpectPasswordOptions(ExpectBase):

    def __init__(self):
        self._options = {}
        self._rest = ''

    def more(self):
        return len(self._options) < 20

    def fill(self, text):
        text = self._rest + text
        self._rest = ''
        while '\r\n' in text:
            line, text = text.split('\r\n', 1)
            if not line:
                continue
            for item in line.split('   '):
                assert ': ' in item, "Unexpected password completer line: %r" \
                                     % item
                shortcut, password = item.split(': ')
                assert len(shortcut) == 1, "Expecting 1 char as shortcut"
                self._options[shortcut] = password
        if not self.more():
            return text
        else:
            self._rest = text

    def check(self):
        assert len(self._options) == 20
        assert len(self._rest) == 0

    def option(self, shortcut):
        assert shortcut in self._options
        return self._options[shortcut]


class Send:

    def __init__(self, text):
        self._text = text

    def __call__(self, p, **kwargs):
        p.write(self._text)
        p.flush()


class SendControl:

    def __init__(self, char):
        self._char = char

    def __call__(self, p, **kwargs):
        p.sendcontrol(self._char)


class Wait:

    def __init__(self, seconds):
        self._seconds = seconds

    def __call__(self, p, **kwargs):
        time.sleep(self._seconds)


filename = '/tmp/test_keybox.gpg'
passphrase = 'secret'
expect_password_options = ExpectPasswordOptions()


@pytest.yield_fixture()
def spawn_keys():
    p = ptyprocess.PtyProcessUnicode.spawn(
        [sys.executable, "-m", "keys", "-f", filename,
         '--no-memlock', '--timeout', '1'],
        echo=False)
    yield p
    p.close(force=True)


@pytest.yield_fixture(scope="module")
def keybox_file():
    yield
    os.unlink(filename)


def run_script(p, script):
    # Use copy of script, let original script unmodified
    script_copy = script[:]
    poll = select.poll()
    poll.register(p.fileno(), select.POLLIN)
    while True:
        cmd = script_copy.pop(0)
        if cmd is None:
            break
        cmd(p, poll=poll, line=len(script) - len(script_copy))

    time.sleep(0.1)
    assert not p.isalive()


@pytest.mark.usefixtures("keybox_file")
def test_shell(spawn_keys):
    run_script(spawn_keys, [
        # Initialize
        Expect("Opening file %r... " % filename),
        Expect("File not found. Create new? [Y/n] "),
        Send("y\n"),
        Expect("Enter passphrase: "),
        Send(passphrase + "\n"),
        Expect("Re-enter passphrase: "),
        Send(passphrase + "\n"),
        # Shell completer
        Expect("> "),
        Send("\t\t"),
        Expect("add      delete   list     nowrite  quit     select   \n"
               "count    help     modify   print    reset    write    "),
        Send("m\t \t\t"),
        Expect("mtime     note      password  site      tags      url       "
               "user"),
        Send("pa\t \tblah\n"),
        Expect("No record selected. See `help select`."),
        # Add command
        Expect("> "),
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
        Expect("> "),
        Send("l\n"),
        ExpectMatch("Example  jackinthebox  http://example.com/  web test  "),
        # Count
        Expect("> "),
        Send("c\n"),
        Expect("1"),
        # Select
        Expect("> "),
        Send("s\n"),
        ExpectMatch("Example  jackinthebox  http://example.com/  web test  "),
        # Print
        Expect("> "),
        Send("p\n"),
        Expect(expect_password_options.option, "6"),
        # Finish
        Expect("> "),
        SendControl("c"),
        Expect("quit"),
        Expect("Changes saved to /tmp/test_keybox.gpg."),
        None,
    ])


@pytest.mark.usefixtures("keybox_file")
def test_timeout(spawn_keys):
    run_script(spawn_keys, [
        # Initialize
        Expect("Opening file %r... " % filename),
        Expect("Passphrase: "),
        Send(passphrase + "\n"),
        # Finish
        Expect("> "),
        Wait(1.1),
        Expect("quit\nTimeout after 1 seconds."),
        None,
    ])
