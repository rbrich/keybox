# Encryption envelope
# This module adds/removes the encryption layer from a keybox file.

import nacl.pwhash
import nacl.utils
import nacl.secret
import base64
from io import BytesIO
import struct

# Header format (integers are little endian):
# 4 bytes MAGIC - zero-terminated string "[K]"
# 4 bytes META_SIZE - total size of the following metadata chunks
# META_SIZE bytes META_DATA - chunks, see below
#
# Each chunk:
# 1 byte TAG
# 1 byte SIZE
# SIZE bytes VALUE
#
# Supported tags:
# 0 - reserved (could be version)
# 1 - DATA_SIZE - size of encrypted data that follow the header - 32bit unsigned integer
# 2 - CIPHER - symmetric encryption algorithm, 8bit unsigned integer:
#              1 = XSalsa20 + Poly1305 MAC (default)
# 3 - PWHASH - key derivation function, 8bit unsigned integer:
#              1 = scrypt
#              2 = argon2i (default)
#              3 = argon2id
# 4 - SALT - string
# 5 - OPS_LIMIT - 8bit unsigned integer
# 6 - MEM_LIMIT - 32bit unsigned integer

MAGIC = b'[K]\0'  # nul byte marks the file as binary without depending on the content itself
TAG_DATA_SIZE = 1
TAG_CIPHER = 2
TAG_PWHASH = 3
TAG_SALT = 4
TAG_OPS_LIMIT = 5
TAG_MEM_LIMIT = 6
CIPHER_XSALSA20_POLY1305 = 1
PWHASH_SCRYPT = 1
PWHASH_ARGON2I = 2
PWHASH_ARGON2ID = 3
PWHASH_MODULE = {
    PWHASH_SCRYPT: nacl.pwhash.scrypt,
    PWHASH_ARGON2I: nacl.pwhash.argon2i,
    PWHASH_ARGON2ID: nacl.pwhash.argon2id,
}


class Envelope:

    def __init__(self):
        # Initialize new file (can be replaced by open method)
        self._pwhash_algo = PWHASH_ARGON2I
        self._pwhash = nacl.pwhash.argon2i
        self._sym_algo = nacl.secret.SecretBox
        self._box = None
        self._key = None
        self._salt = nacl.utils.random(self._pwhash.SALTBYTES)
        self._ops_limit = self._pwhash.OPSLIMIT_INTERACTIVE
        self._mem_limit = self._pwhash.MEMLIMIT_INTERACTIVE

    def _derive_key(self, passphrase: str) -> bytes:
        return self._pwhash.kdf(self._sym_algo.KEY_SIZE,
                                passphrase.encode('utf-8'), self._salt,
                                opslimit=self._ops_limit, memlimit=self._mem_limit)

    @staticmethod
    def _write_chunk(f: BytesIO, tag: int, value: bytes):
        assert len(value) < 256
        f.write(struct.pack('B', tag))
        f.write(struct.pack('B', len(value)))
        f.write(value)

    def write_header(self, f, data_size: int):
        chunks = BytesIO()
        self._write_chunk(chunks, TAG_DATA_SIZE, struct.pack('<I', data_size))
        self._write_chunk(chunks, TAG_CIPHER, struct.pack('<B', CIPHER_XSALSA20_POLY1305))
        self._write_chunk(chunks, TAG_PWHASH, struct.pack('<B', self._pwhash_algo))
        self._write_chunk(chunks, TAG_SALT, self._salt)
        self._write_chunk(chunks, TAG_OPS_LIMIT, struct.pack('<B', self._ops_limit))
        self._write_chunk(chunks, TAG_MEM_LIMIT, struct.pack('<I', self._mem_limit))
        meta_data = chunks.getvalue()
        meta_size = struct.pack('<I', len(meta_data))
        f.write(MAGIC)
        f.write(meta_size)
        f.write(meta_data)

    def read_header(self, f) -> int:
        """Load header (metadata) from stream `f`
        :returns data_size - Size of the encrypted data in bytes,
                             or -1 if not available (the chunk is optional)
        """
        assert f.read(4) == MAGIC
        meta_size = struct.unpack('<I', f.read(4))[0]
        meta_data = f.read(meta_size)
        data_size = -1
        chunks = BytesIO(meta_data)
        while True:
            # read a chunk
            raw_tag_size = chunks.read(2)
            if len(raw_tag_size) == 0:
                break  # no more chunks
            tag, size = struct.unpack('BB', raw_tag_size)
            value = chunks.read(size)
            if tag == TAG_DATA_SIZE:
                data_size = struct.unpack('<I', value)[0]
            elif tag == TAG_CIPHER:
                assert struct.unpack('<B', value)[0] == CIPHER_XSALSA20_POLY1305
            elif tag == TAG_PWHASH:
                self._pwhash_algo = struct.unpack('<B', value)[0]
                self._pwhash = PWHASH_MODULE[self._pwhash_algo]
            elif tag == TAG_SALT:
                self._salt = value
            elif tag == TAG_OPS_LIMIT:
                self._ops_limit = struct.unpack('<B', value)[0]
            elif tag == TAG_MEM_LIMIT:
                self._mem_limit = struct.unpack('<I', value)[0]
            else:
                print(f"WARNING: File contains unknown chunk with tag {tag}, size {size}. "
                      "It might be created by future version of keybox program. Please update...")
        return data_size

    def set_passphrase(self, passphrase: str):
        """Derive a key from `passphrase`"""
        self._key = self._derive_key(passphrase)
        self._box = self._sym_algo(self._key)

    def check_passphrase(self, passphrase: str) -> bool:
        key_check = self._derive_key(passphrase)
        return self._key == key_check

    def write(self, f, data: bytes):
        """Complete encryption, writes header + encrypted data to stream `f`"""
        encrypted = self.encrypt(data)
        self.write_header(f, len(encrypted))
        f.write(encrypted)

    def read(self, f, passphrase_cb) -> bytes:
        """Complete decryption, reads header, asks for passphrase, decrypts data
        :param f                File or IO stream
        :param passphrase_cb    Called to ask passphrase, must return str
        :returns decrypted data
        """
        data_size = self.read_header(f)
        encrypted = f.read(data_size)
        self.set_passphrase(passphrase_cb())
        return self.decrypt(encrypted)

    def encrypt(self, data: bytes) -> bytes:
        """Raw encryption. Metadata are not saved."""
        nonce = nacl.utils.random(self._sym_algo.NONCE_SIZE)
        return self._box.encrypt(data, nonce)

    def decrypt(self, data: bytes) -> bytes:
        """Raw decryption. Metadata must match."""
        return self._box.decrypt(data)

    def encrypt_base64(self, value: str) -> str:
        """Raw encryption + Base64 encoding"""
        data = self.encrypt(value.encode('utf-8'))
        return base64.b64encode(data).decode()

    def decrypt_base64(self, b64_data: str) -> str:
        """Base64 decoding + raw decryption"""
        data = base64.b64decode(b64_data.encode(), validate=True)
        return self.decrypt(data).decode('utf-8')


if __name__ == '__main__':
    def self_test():
        msg = "a message"
        pw = "test"
        print("* Deriving key...")
        box = Envelope()
        box.set_passphrase(pw)
        print("* Encrypt a value...")
        enc1 = box.encrypt_base64(msg)
        print(enc1)
        print("* Encrypt the same value with different nonce...")
        enc2 = box.encrypt_base64(msg)
        print(enc2)
        assert box.decrypt_base64(enc1) == msg
        assert box.decrypt_base64(enc2) == msg
        print("* Complete encryption with header...")
        f = BytesIO()
        box.write(f, msg.encode())
        enc3 = f.getvalue()

        import binascii
        print(enc3)
        print(binascii.hexlify(enc3))
        print("* Reset - deriving key...")
        box = Envelope()
        f = BytesIO(enc3)
        assert box.read(f, lambda: pw).decode() == msg
        assert f.read() == b''  # EOF
    self_test()
