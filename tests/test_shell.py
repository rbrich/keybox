import sys
import shutil
import time
import re
from pathlib import Path
from inspect import currentframe

import pytest

from keybox.main import main as keybox_main
from keybox.shell import ShellUI, BaseInput


class Expect:

    def __init__(self, expected, args=None, regex=False):
        """Match stdout against `expected`
        :param expected: Either string or callable with optional args
        :param args: Args for callable(expected)
        :param regex: Match string as regex. Default is verbatim.
        """
        self._lineno = currentframe().f_back.f_lineno
        self._expected = expected
        self._args = args
        self._regex = regex

    def __repr__(self):
        return f"line {self._lineno}: {self.__class__.__name__}({self._expected!r})"

    def expect(self, actual):
        if callable(self._expected):
            expected = self._expected(*self._args)
        else:
            expected = self._expected
        if self._regex:
            assert re.fullmatch(expected, actual) is not None
        else:
            assert actual == expected, repr(self)

    def send(self):
        raise Exception("Expecting output, not input!")


class Send:

    def __init__(self, text):
        self._text = text

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._text)

    def expect(self, output):
        raise Exception(f"Expecting input, got output: {output!r}")

    def send(self):
        return self._text


class DelayedSend:

    def __init__(self, seconds, text):
        self._seconds = seconds
        self._text = text

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._seconds)

    def expect(self, _):
        raise Exception("Wait: Not expecting output!")

    def send(self):
        time.sleep(self._seconds)
        return self._text


config_filename = 'test_keybox.conf'
safe_filename = 'test_keybox.safe'
passphrase = 'secret'
dummy_filename = Path(__file__).parent / "dummy_keybox.safe"
dummy_passphrase = "test123"


@pytest.fixture()
def config_file(tmp_path):
    return tmp_path / config_filename


@pytest.fixture()
def safe_file(tmp_path):
    return tmp_path / safe_filename


def run_script(monkeypatch, capfd, argv, script):

    def check_captured():
        captured = capfd.readouterr()
        assert captured.err == ''
        if captured.out:
            cmd = script.pop(0)
            cmd.expect(captured.out)

    def expect_print(_self, text, end='\n'):
        if sys.exc_info()[0] is not None:
            # Already handling an exception, passthrough to stdout
            print(text, end=end)
            return
        check_captured()
        cmd = script.pop(0)
        cmd.expect(str(text) + end)

    def feed_input(_self, prompt):
        check_captured()
        script.pop(0).expect(prompt)
        return script.pop(0).send()

    def dummy(*_args, **_kwargs):
        pass

    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError

    monkeypatch.setattr(ShellUI, '_print', expect_print, raising=True)
    monkeypatch.setattr(ShellUI, '_input', feed_input, raising=True)
    monkeypatch.setattr(ShellUI, '_input_pass', feed_input, raising=True)
    monkeypatch.setattr(BaseInput, '__init__', dummy, raising=True)
    monkeypatch.setattr(BaseInput, 'input', feed_input, raising=True)
    monkeypatch.setattr(BaseInput, 'cancel', raise_timeout, raising=True)

    keybox_main(argv)
    check_captured()
    assert len(script) == 0


def test_shell(monkeypatch, capfd, config_file, safe_file):
    assert not safe_file.exists()
    temp_pass = 'temporary_password'
    argv = ["shell", "-c", str(config_file), "-f", str(safe_file),
            '--timeout', '100']
    run_script(monkeypatch, capfd, argv, [
        # Initialize
        Expect(f"Loading config {str(config_file)!r}...\n"),
        Expect(f"Opening file {str(safe_file)!r}... "),
        Expect(f"Not found.\n"),
        Expect("Create new keybox file? [Y/n] "),
        Send("y"),
        Expect("Enter new passphrase: "),
        Send(temp_pass),
        Expect("Re-enter new passphrase: "),
        Send(temp_pass),
        # Shell completer
        Expect("> "),
        Send("m p blah"),
        Expect("No record selected. See `help select`.\n"),
        # Add command
        Expect("> "),
        Send("add"),
        Expect("User:     "),
        Send("jackinthebox"),
        Expect("Password: "),
        Send("pw123"),
        Expect("Site:     "),
        Send("Example"),
        Expect("URL:      "),
        Send("http://example.com/"),
        Expect("Tags:     "),
        Send("web test"),
        Expect("Note:     "),
        Send(""),
        # List
        Expect("> "),
        Send("l"),
        Expect("Example  jackinthebox  http://example.com/  web test  "
               "%s \\d{2}:\\d{2}:\\d{2}    \n" % time.strftime("%F"),
               regex=True),
        # Count
        Expect("> "),
        Send("count"),
        Expect("1\n"),
        # Write
        Expect("> "),
        Send("w"),
        Expect(f"Changes saved to file {str(safe_file)!r}.\n"),
        # Select
        Expect("> "),
        Send("s"),
        Expect("Example  jackinthebox  http://example.com/  web test  "
               "%s \\d{2}:\\d{2}:\\d{2}    \n" % time.strftime("%F"),
               regex=True),
        # Print
        Expect("> "),
        Send("p"),
        Expect("pw123\n"),
        # Select with args
        Expect("> "),
        Send("select nonexisting"),
        Expect("Not found.\n"),
        Expect("> "),
        Send("select example"),
        Expect("Example  jackinthebox  http://example.com/  web test  "
               "%s \\d{2}:\\d{2}:\\d{2}    \n" % time.strftime("%F"),
               regex=True),
        # Reset
        Expect("> "),
        Send("reset"),
        Expect("Enter current passphrase: "),
        Send(temp_pass),
        Expect("Enter new passphrase: "),
        Send(passphrase),
        Expect("Re-enter new passphrase: "),
        Send(passphrase),
        # Is the password still okay after re-encryption?
        Expect("> "),
        Send("p"),
        Expect("pw123\n"),
        # Check
        Expect("> "),
        Send("ch"),
        # Delete
        Expect("> "),
        Send("d"),
        Expect("Delete selected record? This cannot be taken back! [y/n] "),
        Send("y"),
        Expect("Record deleted.\n"),
        # Finish
        Expect("> "),
        Send("quit"),
        Expect(f"Changes saved to file {str(safe_file)!r}.\n"),
    ])


def test_timeout(monkeypatch, capfd, config_file, safe_file):
    shutil.copyfile(dummy_filename, safe_file)
    argv = ["shell", "-c", str(config_file), "-f", str(safe_file),
            '--timeout', '1']
    run_script(monkeypatch, capfd, argv, [
        # Initialize
        Expect(f"Loading config {str(config_file)!r}...\n"),
        Expect(f"Opening file {str(safe_file)!r}... "),
        Expect("\n"),
        Expect("Passphrase: "),
        Send(dummy_passphrase),
        # Finish
        Expect("> "),
        DelayedSend(1.1, "too late"),
        Expect("Timeout after 1 seconds.\n"),
    ])
