# encrypt, decrypt
# (call gpg system command)
#

from subprocess import Popen, PIPE

CIPHER = 'AES256'
DIGEST = 'SHA512'
S2K_COUNT = 65011712 / 100  # Bigger number means slower cracking


def _call(args: list, data: bytes) -> bytes:
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    outs, errs = p.communicate(data)
    if p.returncode != 0:
        raise Exception(errs.decode().strip())
    return outs


def encrypt(data: bytes, passphrase: str, cipher=CIPHER, digest=DIGEST,
            s2k_count=S2K_COUNT) -> bytes:
    """Encrypt `data` with `passphrase`."""
    gpg_args = ['gpg', '--quiet', '--batch', '--symmetric',
                '--passphrase', passphrase,
                '--s2k-digest-algo', digest,
                '--s2k-mode', str(3 if s2k_count > 1 else 1),
                '--s2k-count', str(s2k_count),
                '--cipher-algo', cipher]
    return _call(gpg_args, data)


def decrypt(data: bytes, passphrase: str) -> bytes:
    """Decrypt encrypted `data` using `passphrase`.

    Throw Exception on invalid passphrase.

    """
    gpg_args = ['gpg', '--quiet', '--batch', '--decrypt',
                '--passphrase', passphrase]
    return _call(gpg_args, data)
