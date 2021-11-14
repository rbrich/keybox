import pytest
from pathlib import Path

from keybox.datasafe import DataSafeUI


data_file_name = 'test_keybox.data'
safe_file_name = 'test_keybox.data.safe'
data_content = b"lorem ipsum dolor sit amet"


class Expect:

    def __init__(self, s):
        self._s = s

    def expect(self, actual):
        assert self._s == actual

    def send(self):
        raise Exception("Expecting output, not input!")


class Send:

    def __init__(self, s):
        self._s = s

    def expect(self, _):
        raise Exception("Expecting input, not output!")

    def send(self):
        return self._s


def test_data_safe(tmp_path, monkeypatch):
    data_file = tmp_path / data_file_name
    data_file.write_bytes(data_content)
    safe_file = tmp_path / safe_file_name

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
        Expect(f"Removed encrypted file {str(safe_file)!r}")
    ]

    def expect_print(_self, s):
        expected.pop(0).expect(s)

    def feed_input(_self, prompt):
        expected.pop(0).expect(prompt)
        return expected.pop(0).send()

    monkeypatch.setattr(DataSafeUI, '_print', expect_print, raising=True)
    monkeypatch.setattr(DataSafeUI, '_input', feed_input, raising=True)
    monkeypatch.setattr(DataSafeUI, '_input_pass', feed_input, raising=True)

    # Encrypt
    safe_ui = DataSafeUI(safe_file)
    assert safe_ui.create()
    safe_ui.encrypt_file(data_file)
    safe_ui.close()

    # Decrypt
    safe_ui = DataSafeUI(safe_file)
    assert safe_ui.open()
    assert safe_ui.decrypt_file(data_file)
    safe_ui.close(unlink=True)

    assert len(expected) == 0
