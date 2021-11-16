# Encrypt/decrypt a plain data file

from pathlib import Path

from .envelope import Envelope
from .ui import BaseUI


class DataSafe:

    """Secure box for any data"""

    def __init__(self):
        self._envelope = Envelope()

    def set_passphrase(self, new_passphrase):
        self._envelope.set_passphrase(new_passphrase)

    def read_data(self, encrypted_file, passphrase_cb) -> bytes:
        """Read contained data from `encrypted_file`.
        Used for direct decryption of a .safe file."""
        return self._envelope.read(encrypted_file, passphrase_cb)

    def write_data(self, encrypted_file, data: bytes):
        """Write `data` to `encrypted_file`.
        Used for direct encryption to a .safe file."""
        self._envelope.write(encrypted_file, data)


class DataSafeUI(BaseUI):

    def __init__(self, filename: Path):
        self._filename = filename
        self._filename_tmp = self._filename.with_suffix(self._filename.suffix + '.tmp')
        self._wfile = None
        self._safe = DataSafe()

    def __del__(self):
        self.close()

    def create(self):
        print("Creating file %r..." % str(self._filename))
        if self._filename.exists():
            if not self._ask_yesno("Target file exists. Overwrite?"):
                return False
        passphrase = self._input_pass("Enter new passphrase: ")
        passphrase_check = self._input_pass("Re-enter new passphrase: ")
        if passphrase != passphrase_check:
            print("Not same...")
            return False
        self._safe.set_passphrase(passphrase)
        return True

    def open(self):
        print("Opening file %r..." % str(self._filename))
        if not self._filename.exists():
            print("Not found.")
            return False
        self._filename.replace(self._filename_tmp)
        return True

    def close(self, unlink=False):
        if not self._filename_tmp.exists():
            return
        if unlink:
            self._filename_tmp.unlink()
            print(f"Removed encrypted file {str(self._filename)!r}")
            return
        self._filename_tmp.rename(self._filename)

    ###################
    # Encrypt/Decrypt #
    ###################

    def encrypt_file(self, plain_file: Path):
        with open(plain_file, 'rb') as f:
            data = f.read()
        with self._filename_tmp.open('wb') as f:
            self._safe.write_data(f, data)
        self._filename_tmp.rename(self._filename)
        print(f"Encrypted to file {str(self._filename)!r}.")

    def decrypt_file(self, plain_file: Path):
        if plain_file.exists():
            if not self._ask_yesno("Target file exists. Overwrite?"):
                return False
        with open(self._filename_tmp, 'rb') as f:
            data = self._safe.read_data(f, lambda: self._input_pass("Passphrase: "))
        with open(plain_file, 'wb') as f:
            f.write(data)
        print(f"Decrypted to file {str(plain_file)!r}.")
        return True
