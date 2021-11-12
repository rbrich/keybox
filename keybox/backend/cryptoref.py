from cryptoref import xsalsa20poly1305_encrypt, xsalsa20poly1305_decrypt


class XSalsa20Poly1305:

    """Implements NaCL SecretBox recipe"""

    NONCE_SIZE = 24
    KEY_SIZE = 32

    def __init__(self, key: bytes):
        self._key = key

    def encrypt(self, message: bytes, nonce: bytes) -> bytes:
        return nonce + xsalsa20poly1305_encrypt(message, nonce, bytes(self._key))

    def decrypt(self, ciphertext: bytes) -> bytes:
        return xsalsa20poly1305_decrypt(ciphertext[24:], ciphertext[:24], bytes(self._key))


if __name__ == '__main__':
    def self_test():
        import binascii
        nonce = 24 * b'#'
        key = 32 * b'$'
        x = XSalsa20Poly1305(key)
        plaintext = b"test data"
        ciphertext = x.encrypt(plaintext, nonce)
        print(len(ciphertext), binascii.hexlify(ciphertext))
        assert x.decrypt(ciphertext) == plaintext
    self_test()
