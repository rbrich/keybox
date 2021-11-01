# Encryption envelope
# This module adds/removes the encryption layer from a keybox file.

import base64
import struct
from io import BytesIO

from .backend import *


# Header format
# =============
# 4 bytes MAGIC - zero-terminated string "[K]"
# 4 bytes META_SIZE (u32) - total size of the following metadata chunks
# META_SIZE bytes META_DATA - chunks, see below
#
# Each chunk:
# 1 byte TAG
# 1 byte SIZE
# SIZE bytes VALUE
#
# Supported tags:
# 0 - END - terminates the chunk reading, allows extra data in the header
#           (the chunk SIZE must follow, making the terminator a sequence of two zero bytes)
# 1 - DATA_SIZE (u32) - size of encrypted data that follows the header
# 2 - PLAIN_SIZE (u32) - size of plain data (decrypted and decompressed)
# 3 - COMPRESSION (u8) - data can be compressed before being encrypted
#               0 - no compression
#               1 - zlib deflate, window bits = -15 (default)
# 4 - CIPHER (u8) - symmetric encryption algorithm:
#               1 = XSalsa20 + Poly1305 MAC (default)
# 5 - KDF (u8) - key derivation function, used for key stretching (password -> cryptographic key):
#               (0 = none, passphrase is raw key)
#               1 = argon2id (default)
# 6 - KDF_PARAMS (var) - KDF parameters, must appear after the KDF tag in the header
#               argon2 - SIZE=4: version (u8), mem_cost (u8), time_cost (u8), threads (u8)
#               NOTE: actual memory usage is derived as 2^N KiB
# 7 - SALT (str) - a salt to seed the KDF
# 8 - CRC32 (u32) - checksum of plain data
#
# Types:
# (u8, u16, u32, u64) unsigned integers, little endian
#       - the size in the above specification is the default for writing
#       - when reading, the integer size is controlled by the chunk SIZE
# (str) string of bytes / binary data - the length is limited by 1 byte SIZE, i.e. 255
#
# Extension points:
# - META_DATA area can be bigger than the contained chunks (last chunk can be '\0\0' - a terminator)
#       - anything after the marker is currently ignored
# - 8 + META_SIZE + DATA_SIZE can be smaller than the actual file
#       - anything after the encrypted data and before EOF is currently ignored
# - every integer field supports all sizes (8bit to 64bit)
#       - DATA_SIZE can be 64bit, only META_SIZE is truly limited to 32bit
#       - CIPHER, PWHASH enums can extend to another byte if needed
# - no versioning, the program tries to read the file and ignores unknown chunks (emits a warning)
#       - this allows adding new optional chunks without breaking the ability of old versions
#         of the program to read it (if it were driven by a version, the old program would be
#         obliged to reject the file)

MAGIC = b'[K]\0'  # nul byte marks the file as binary without depending on the content itself

TAG_END = 0
TAG_DATA_SIZE = 1
TAG_PLAIN_SIZE = 2
TAG_COMPRESSION = 3
TAG_CIPHER = 4
TAG_KDF = 5
TAG_KDF_PARAMS = 6
TAG_SALT = 7
TAG_CRC32 = 8

COMPRESSION_NONE = 0
COMPRESSION_DEFLATE = 1

KDF_ARGON2ID = 1
KDF_BY_ID = {
    KDF_ARGON2ID: argon2id,
}
KDF_PARAMS_BY_ID = {
    KDF_ARGON2ID: Argon2Params,
}

CIPHER_XSALSA20_POLY1305 = 1

CIPHER_BY_ID = {
    CIPHER_XSALSA20_POLY1305: XSalsa20Poly1305,
}

COMPRESS_BY_ID = {
    COMPRESSION_NONE: noop_compress,
    COMPRESSION_DEFLATE: deflate_compress,
}

DECOMPRESS_BY_ID = {
    COMPRESSION_NONE: noop_decompress,
    COMPRESSION_DEFLATE: deflate_decompress,
}

SALT_SIZE = 16


class Envelope:

    def __init__(self):
        # Initialize new file (can be replaced by open method)
        self._kdf_id = KDF_ARGON2ID
        self._kdf = KDF_BY_ID[self._kdf_id]
        self._kdf_params = KDF_PARAMS_BY_ID[self._kdf_id]()
        self._cipher_id = CIPHER_XSALSA20_POLY1305
        self._cipher = CIPHER_BY_ID[self._cipher_id]
        self._compression_id = COMPRESSION_DEFLATE
        self._compress = COMPRESS_BY_ID[self._compression_id]
        self._decompress = DECOMPRESS_BY_ID[self._compression_id]
        self._box = None
        self._key = None
        self._salt = randombytes(SALT_SIZE)

    def _derive_key(self, passphrase: str) -> bytes:
        return self._kdf(passphrase.encode('utf-8'), self._salt, self._cipher.KEY_SIZE,
                         self._kdf_params)

    @staticmethod
    def _write_chunk(f: BytesIO, tag: int, value: bytes):
        assert len(value) < 256
        f.write(struct.pack('B', tag))
        f.write(struct.pack('B', len(value)))
        f.write(value)

    def write_header(self, f, data_size: int, plain_size: int, checksum: int):
        chunks = BytesIO()
        self._write_chunk(chunks, TAG_DATA_SIZE, struct.pack('<L', data_size))
        self._write_chunk(chunks, TAG_PLAIN_SIZE, struct.pack('<L', plain_size))
        self._write_chunk(chunks, TAG_COMPRESSION, struct.pack('<B', self._compression_id))
        self._write_chunk(chunks, TAG_CIPHER, struct.pack('<B', self._cipher_id))
        self._write_chunk(chunks, TAG_KDF, struct.pack('<B', self._kdf_id))
        self._write_chunk(chunks, TAG_KDF_PARAMS, self._kdf_params.encode())
        self._write_chunk(chunks, TAG_SALT, self._salt)
        self._write_chunk(chunks, TAG_CRC32, struct.pack('<L', checksum))
        meta_data = chunks.getvalue()
        meta_size = struct.pack('<L', len(meta_data))
        f.write(MAGIC)
        f.write(meta_size)
        f.write(meta_data)

    def read_header(self, f) -> tuple:
        """Load header (metadata) from stream `f`

        :return: (data_size, plain_size)

        data_size
            Size of the encrypted data in bytes,
            or -1 if not available (the chunk is optional)
        plain_size
            Size of the decrypted and decompressed data in bytes,
            or -1 if not available (the chunk is optional)
        """
        assert f.read(4) == MAGIC
        meta_size = struct.unpack('<L', f.read(4))[0]
        meta_data = f.read(meta_size)
        data_size = -1
        plain_size = -1
        checksum = None
        chunks = BytesIO(meta_data)

        def unpack_uint(v):
            if len(v) == 1: return struct.unpack('<B', v)[0]
            if len(v) == 2: return struct.unpack('<H', v)[0]
            if len(v) == 4: return struct.unpack('<L', v)[0]
            if len(v) == 8: return struct.unpack('<Q', v)[0]
            raise Exception("Corrupted file envelope (not uint: %r)" % v)

        while True:
            # read a chunk
            raw_tag_size = chunks.read(2)
            if len(raw_tag_size) == 0:
                break  # implicit end of chunks - no more data
            tag, size = struct.unpack('BB', raw_tag_size)
            if tag == TAG_END:
                break  # explicit end of chunks
            value = chunks.read(size)
            if tag == TAG_DATA_SIZE:
                data_size = unpack_uint(value)
            elif tag == TAG_PLAIN_SIZE:
                plain_size = unpack_uint(value)
            elif tag == TAG_COMPRESSION:
                self._compression_id = unpack_uint(value)
                self._compress = COMPRESS_BY_ID[self._compression_id]
                self._decompress = DECOMPRESS_BY_ID[self._compression_id]
            elif tag == TAG_CIPHER:
                self._cipher_id = unpack_uint(value)
                self._cipher = CIPHER_BY_ID[self._cipher_id]
            elif tag == TAG_KDF:
                self._kdf_id = unpack_uint(value)
                self._kdf = KDF_BY_ID[self._kdf_id]
                self._kdf_params = KDF_PARAMS_BY_ID[self._kdf_id]()
            elif tag == TAG_KDF_PARAMS:
                self._kdf_params.decode(value)
            elif tag == TAG_SALT:
                self._salt = value
            elif tag == TAG_CRC32:
                checksum = unpack_uint(value)
            else:
                print(f"WARNING: File contains unknown chunk with tag {tag}, size {size}. "
                      "It might be created by future version of keybox program. Please update...")
        return data_size, plain_size, checksum

    def set_passphrase(self, passphrase: str):
        """Derive a key from `passphrase`"""
        self._key = self._derive_key(passphrase)
        self._box = self._cipher(self._key)

    def check_passphrase(self, passphrase: str) -> bool:
        key_check = self._derive_key(passphrase)
        return self._key == key_check

    def write(self, f, data: bytes):
        """Complete encryption, writes header + encrypted data to stream `f`"""
        checksum = crc32(data)
        plain_size = len(data)
        data = self._compress(data)
        data = self.encrypt(data)
        self.write_header(f, len(data), plain_size, checksum)
        f.write(data)

    def read(self, f, passphrase_cb) -> bytes:
        """Complete decryption, reads header, asks for passphrase, decrypts data

        :param f:               File or IO stream
        :param passphrase_cb:   Called to ask passphrase, must return str
        :return: decrypted data
        """
        data_size, plain_size, checksum = self.read_header(f)
        data = f.read(data_size)
        self.set_passphrase(passphrase_cb())
        data = self.decrypt(data)
        data = self._decompress(data, plain_size)
        assert plain_size == -1 or len(data) == plain_size
        if checksum is not None:
            assert crc32(data) == checksum
        return data

    def encrypt(self, data: bytes) -> bytes:
        """Raw encryption. Metadata are not saved."""
        nonce = randombytes(self._cipher.NONCE_SIZE)
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
        import binascii
        import time
        msg = "a message"
        pw = "test"
        print("* Derive key...")
        box = Envelope()
        # box._salt = b'#'*16
        t = time.time_ns()
        box.set_passphrase(pw)
        t2 = time.time_ns()
        print(f"* Time: {(t2-t)/1e6} ms")
        print("Key:", binascii.hexlify(box._key).decode())
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
        print(binascii.hexlify(enc3))
        print("* Reset - decompress + derive key...")
        box = Envelope()
        f = BytesIO(enc3)
        assert box.read(f, lambda: pw).decode() == msg
        assert f.read() == b''  # EOF
        print("Key:", binascii.hexlify(box._key).decode())
    self_test()
