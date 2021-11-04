# decrypt legacy GPG format

import base64

try:
    # prefer GPGME
    from gpg import Context
except ImportError:
    # fallback to gpg command
    from subprocess import Popen, PIPE

    class Context:

        def __init__(self, **kwargs):
            print("WARNING: GPGME (python3-gpg) not found, falling back to 'gpg' command")

        @staticmethod
        def _call(args: list, data: bytes) -> bytes:
            p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            outs, errs = p.communicate(data)
            if p.returncode != 0:
                raise Exception(errs.decode().strip())
            return outs

        def decrypt(self, data: bytes, passphrase: str, **kwargs):
            gpg_args = ['gpg', '--quiet', '--batch', '--decrypt',
                        '--passphrase', passphrase]
            return self._call(gpg_args, data), None, None


class EnvelopeGPG:

    def __init__(self):
        self._ctx = Context(offline=True)
        self._passphrase = None

    def set_passphrase(self, passphrase: str):
        """Derive a key from `passphrase`"""
        self._passphrase = passphrase

    def read(self, f, passphrase_cb) -> bytes:
        encrypted = f.read()
        self.set_passphrase(passphrase_cb())
        return self.decrypt(encrypted)

    def decrypt(self, data: bytes) -> bytes:
        """Equivalent command: gpg --decrypt --passphrase <passphrase>

        Throw Exception on invalid passphrase.
        """
        plain, _, _ = self._ctx.decrypt(
            data, passphrase=self._passphrase, verify=False)
        return plain

    def decrypt_base64(self, b64_data: str) -> str:
        """Base64 decoding + raw decryption"""
        data = base64.b64decode(b64_data.encode(), validate=True)
        return self.decrypt(data).decode('utf-8')
