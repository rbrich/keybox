import os
import pytest
from pathlib import Path

from keybox.datasafe import DataSafeUI


data_file = Path('/tmp/test_keybox.data')
safe_file = Path('/tmp/test_keybox.data.safe')
data_content = b"lorem ipsum dolor sit amet"


@pytest.fixture
def with_data_file():
    assert not data_file.exists()
    assert not safe_file.exists()
    with data_file.open('wb') as f:
        f.write(data_content)
    try:
        yield
    finally:
        data_file.unlink()


class Expect:

    def __init__(self, s):
        self._s = s

    def expect(self, expected):
        assert self._s == expected

    def send(self):
        raise Exception("Expecting output, not input!")


class Send:

    def __init__(self, s):
        self._s = s

    def expect(self, expected):
        raise Exception("Expecting input, not output!")

    def send(self):
        return self._s


@pytest.mark.usefixtures("with_data_file")
def test_data_safe():
    safe_ui = DataSafeUI(safe_file)

    passphrase = "test pass"

    expected = [
        # Encrypt
        Expect(f"Creating file {str(safe_file)!r}..."),
        Expect("Enter new passphrase: "),
        Send(passphrase),
        Expect("Re-enter new passphrase: "),
        Send(passphrase),
        Expect(f"Encrypted to file {str(safe_file)!r}."),
        # Decrypt
        Expect(f"Opening file {str(safe_file)!r}..."),
        Expect("Target file exists. Overwrite? [Y/n] "),
        Send("y"),
        Expect("Passphrase: "),
        Send(passphrase),
        Expect(f"Decrypted to file {str(data_file)!r}."),
    ]

    def expect_print(s):
        expected.pop(0).expect(s)

    def feed_input(prompt):
        expected.pop(0).expect(prompt)
        return expected.pop(0).send()

    safe_ui._print = expect_print
    safe_ui._input = feed_input
    safe_ui._input_pass = feed_input

    # Encrypt
    assert safe_ui.create()
    safe_ui.encrypt_file(data_file)
    safe_ui.close()

    # Decrypt
    assert safe_ui.open()
    assert safe_ui.decrypt_file(data_file)
    safe_ui.close(unlink=True)
