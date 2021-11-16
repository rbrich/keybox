import shutil
import time
from pathlib import Path
from threading import Event

import pytest

from keybox.main import main as keybox_main
from keybox.ui import BaseUI
from keybox.shell import ShellUI, BaseInput

from .expect import Expect, ExpectCopy, Send, DelayedSend


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


@pytest.fixture()
def prepare_script(monkeypatch, capfd):

    script = []
    timeouted = Event()

    def check_captured():
        captured = capfd.readouterr()
        assert captured.err == ''
        out = captured.out
        while out:
            cmd = script.pop(0)
            out = cmd.expect(out)

    def expect_copy(_self, text):
        check_captured()
        cmd = script.pop(0)
        cmd.expect_copy(str(text))

    def feed_input(_self, prompt):
        check_captured()
        script.pop(0).expect(prompt)
        feed = script.pop(0).send()
        if timeouted.is_set():
            raise TimeoutError
        return feed

    def raise_timeout(*_args, **_kwargs):
        timeouted.set()

    def dummy(*_args, **_kwargs):
        pass

    monkeypatch.setattr(ShellUI, '_input', feed_input, raising=True)
    monkeypatch.setattr(BaseUI, '_input', feed_input, raising=True)
    monkeypatch.setattr(BaseUI, '_input_pass', feed_input, raising=True)
    monkeypatch.setattr(BaseUI, '_copy', expect_copy, raising=True)
    monkeypatch.setattr(BaseInput, '__init__', dummy, raising=True)
    monkeypatch.setattr(BaseInput, 'input', feed_input, raising=True)
    monkeypatch.setattr(BaseInput, 'cancel', raise_timeout, raising=True)

    def prepare(*script_items):
        script.extend(script_items)

    yield prepare

    check_captured()
    assert len(script) == 0


def test_shell(prepare_script, config_file, safe_file):
    assert not safe_file.exists()
    temp_pass = 'temporary_password'
    prepare_script(
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
    )
    keybox_main(["shell", "-c", str(config_file), "-f", str(safe_file),
                 '--timeout', '10'])


def test_timeout(prepare_script, config_file, safe_file):
    shutil.copyfile(dummy_filename, safe_file)
    prepare_script(
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
    )
    keybox_main(["shell", "-c", str(config_file), "-f", str(safe_file),
                 '--timeout', '1'])


def test_readonly(prepare_script, config_file, safe_file):
    shutil.copyfile(dummy_filename, safe_file)
    prepare_script(
        # Initialize
        Expect(f"Loading config {str(config_file)!r}...\n"),
        Expect(f"Opening file {str(safe_file)!r}... \n"),
        Expect("Passphrase: "),
        Send(dummy_passphrase),
        # Check read-only mode
        Expect("Open in read-only mode.\n"),
        Expect("> "),
        Send("reset"),
        Expect("Read-only mode.\n"),
        Expect("> "),
        Send("q"),
    )
    keybox_main(["shell", "-c", str(config_file), "-f", str(safe_file),
                 '--read-only', '--timeout', '1'])


def test_print(prepare_script, config_file, safe_file):
    shutil.copyfile(dummy_filename, safe_file)
    filter_expr = 'test'
    prepare_script(
        # Initialize
        Expect(f"Loading config {str(config_file)!r}...\n"),
        Expect(f"Opening file {str(safe_file)!r}... \n"),
        Expect("Passphrase: "),
        Send(dummy_passphrase),
        # Check read-only mode
        Expect("Open in read-only mode.\n"),
        Expect(f"Searching for '{filter_expr}'...\n"),
        Expect("test  test  http://test.test  test  2021-11-06 20:23:59  test!  \n"),
        Expect('test\n'),  # this is the password
    )
    keybox_main(["print", filter_expr, "-c", str(config_file), "-f", str(safe_file)])


def test_copy(prepare_script, config_file, safe_file):
    shutil.copyfile(dummy_filename, safe_file)
    filter_expr = 'test'
    prepare_script(
        # Initialize
        Expect(f"Loading config {str(config_file)!r}...\n"),
        Expect(f"Opening file {str(safe_file)!r}... \n"),
        Expect("Passphrase: "),
        Send(dummy_passphrase),
        # Check read-only mode
        Expect("Open in read-only mode.\n"),
        Expect(f"Searching for '{filter_expr}'...\n"),
        Expect("test  test  http://test.test  test  2021-11-06 20:23:59  test!  \n"),
        ExpectCopy('test'),  # this is the password
    )
    keybox_main(["copy", filter_expr, "-c", str(config_file), "-f", str(safe_file)])
