from keybox.datasafe import DataSafeUI

from .expect import Expect, Send


data_file_name = 'test_keybox.data'
safe_file_name = 'test_keybox.data.safe'
data_content = b"lorem ipsum dolor sit amet"


def test_data_safe(tmp_path, monkeypatch, capfd):
    data_file = tmp_path / data_file_name
    data_file.write_bytes(data_content)
    safe_file = tmp_path / safe_file_name

    passphrase = "test pass"

    script = [
        # Encrypt
        Expect(f"Creating file {str(safe_file)!r}...\n"),
        Expect("Enter new passphrase: "),
        Send(passphrase),
        Expect("Re-enter new passphrase: "),
        Send(passphrase),
        Expect(f"Encrypted to file {str(safe_file)!r}.\n"),
        # Decrypt
        Expect(f"Opening file {str(safe_file)!r}...\n"),
        Expect("Target file exists. Overwrite? [Y/n] "),
        Send("y"),
        Expect("Passphrase: "),
        Send(passphrase),
        Expect(f"Decrypted to file {str(data_file)!r}.\n"),
        Expect(f"Removed encrypted file {str(safe_file)!r}\n")
    ]

    def check_captured():
        captured = capfd.readouterr()
        assert captured.err == ''
        out = captured.out
        while out:
            cmd = script.pop(0)
            out = cmd.expect(out)

    def feed_input(_self, prompt):
        check_captured()
        script.pop(0).expect(prompt)
        return script.pop(0).send()

    monkeypatch.setattr(DataSafeUI, '_input', feed_input, raising=True)
    monkeypatch.setattr(DataSafeUI, '_input_pass', feed_input, raising=True)

    # Encrypt
    safe_ui = DataSafeUI(safe_file)
    assert safe_ui.create()
    safe_ui.encrypt_file(data_file)
    safe_ui.close()
    check_captured()

    # Decrypt
    safe_ui = DataSafeUI(safe_file)
    assert safe_ui.open()
    assert safe_ui.decrypt_file(data_file)
    safe_ui.close(unlink=True)
    check_captured()

    assert len(script) == 0
