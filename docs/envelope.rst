Envelope
========

The envelope provides compression, encryption and validation
for the wrapped internal file (see :doc:`format`).

The envelope has a header, which is immediately followed by the encrypted data.

Header format
-------------

| **4 bytes MAGIC** - zero-terminated string: "[K]"
| **4 bytes META_SIZE** (u32) - total size of the following metadata chunks
| **META_SIZE bytes META_DATA** - metadata chunks, see below

Chunk format
------------

| **1 byte TAG**
| **1 byte SIZE**
| **SIZE bytes VALUE**

Supported tags:

0 - END
    Terminates the chunk reading, allows extra data in the header
    (the chunk SIZE must follow, making the terminator a sequence of two zero bytes)

1 - DATA_SIZE (u32)
    Size of encrypted data that follows the header

2 - PLAIN_SIZE (u32)
    Size of plain data (decrypted and decompressed)

3 - COMPRESSION (u8)
    Internal data can be compressed before being encrypted

    | 0 - no compression
    | 1 - zlib deflate, window bits = -15 (default)

4 - CIPHER (u8)
    Symmetric encryption algorithm:

    | 1 = XSalsa20 + Poly1305 MAC (default)

5 - KDF (u8)
    Key derivation function, used for key stretching (password -> cryptographic key):

    | (0 = none, passphrase is raw key)
    | 1 = argon2id (default)

6 - KDF_PARAMS (var)
    KDF parameters, must appear after the KDF tag in the header

    | argon2 - SIZE=4: version (u8), mem_cost (u8), time_cost (u8), threads (u8)
    |          NOTE: actual memory usage is derived as 2^N KiB

7 - SALT (str)
    A salt to seed the KDF

8 - CRC32 (u32)
    Checksum of plain data

Value types:

(u8, u16, u32, u64)
    - unsigned integers, little endian
    - the size in the above specification is the default for writing
    - when reading, the integer size is controlled by the chunk SIZE

(str)
    - string of bytes / binary data
    - the length is limited by 1 byte SIZE, i.e. 255

Extension points
----------------

- META_DATA area can be bigger than the contained chunks

  - last chunk can be END marker ('\0\0')
  - anything after the marker is currently ignored

- 8 + META_SIZE + DATA_SIZE can be smaller than the actual file

  - anything after the encrypted data and before EOF is currently ignored

- every integer field supports all sizes (8bit to 64bit)

  - DATA_SIZE can be 64bit, only META_SIZE is truly limited to 32bit
  - CIPHER, PWHASH enums can extend to another byte if needed

- no version

  - the program tries to read the file and ignores unknown chunks (emits a warning)
  - this allows adding new optional chunks without breaking the ability of old versions
    of the program to read it (if it were driven by a version, the old program would be
    obliged to reject the file)
