from keybox.backend import SecureMemory


def test_secure_memory():
    b = b"sensitive data"
    c = b' '.join([b"sensitive", b"data"])
    assert id(c) != id(b)
    m = SecureMemory(b)
    assert bytes(m) == c
    del m
    assert b == b'\0' * len(c)
