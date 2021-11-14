# backends provided by Python Standard Library

import os
import zlib
from io import BytesIO
from contextlib import contextmanager
from threading import Timer


def noop_compress(data: bytes) -> bytes:
    return data


def noop_decompress(data: bytes, _plain_size=-1) -> bytes:
    return data


def deflate_compress(data: bytes) -> bytes:
    c = zlib.compressobj(level=9, wbits=-15, memLevel=9)
    out = BytesIO()
    out.write(c.compress(data))
    out.write(c.flush())
    return out.getvalue()


def deflate_decompress(data: bytes, plain_size=-1) -> bytes:
    return zlib.decompress(data, wbits=-15,
                           bufsize=zlib.DEF_BUF_SIZE if plain_size == -1 else plain_size)


crc32 = zlib.crc32

randombytes = os.urandom


@contextmanager
def timeout(secs: float, handler):
    t = Timer(secs, handler)
    t.start()
    try:
        yield
    finally:
        t.cancel()
