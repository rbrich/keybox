import ctypes
from ctypes.util import find_library
import sys
import os
import errno
import resource

libc = ctypes.CDLL(find_library("c"), use_errno=True)


def memory_lock(addr, len):
    """Try to lock an address against being swapped.

    Encountering error while locking memory is not considered fatal,
    no exception is raised.

    """
    # Set MEMLOCK soft limit to maximum
    limits = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (limits[1], limits[1]))
    try:
        rc = libc.mlock(ctypes.c_void_p(addr), len)
    except OSError as e:
        print("Warning: Unable to lock memory.", str(e))
        return
    if rc == -1:  # pragma: no cover
        err = ctypes.get_errno()
        if err == errno.ENOMEM:
            limit = resource.getrlimit(resource.RLIMIT_MEMLOCK)[1]
            print("Warning: Unable to lock memory.",
                  "Consider raising MEMLOCK limit (current %d)." % limit)
        else:
            print("Error (mlock):", errno.errorcode[err], os.strerror(err))


def memory_unlock(addr, len):
    try:
        rc = libc.munlock(ctypes.c_void_p(addr), len)
    except OSError as e:
        print("Warning: Unable to unlock memory.", str(e))
        return
    if rc == -1:  # pragma: no cover
        err = ctypes.get_errno()
        print("Error (munlock):", errno.errorcode[err], os.strerror(err))


def memory_clear(addr, len):
    try:
        rc = libc.memset(ctypes.c_void_p(addr), 0, len)
    except OSError as e:
        print("Warning: Unable to clear memory.", str(e))
        return
    if rc == -1:  # pragma: no cover
        err = ctypes.get_errno()
        print("Error (memset):", errno.errorcode[err], os.strerror(err))


class SecureMemory:

    """Memlock the memory (do not allow swap).

    Zero the memory in deleter. This is a little hacky,
    it depends on CPython and it's bytes object implementation.

    """

    def __init__(self, data: bytes):
        self._data = data
        addr = id(self._data)
        size = sys.getsizeof(self._data)
        memory_lock(addr, size)

    def __del__(self):
        addr = id(self._data)
        brutto = sys.getsizeof(self._data)
        netto = len(self._data)
        # CPython assumption:
        # bytes object has header, followed by data and 1 byte terminator
        memory_clear(addr + (brutto - netto - 1), netto)
        memory_unlock(addr, brutto)

    def __bytes__(self):
        return self._data

    def __eq__(self, other):
        return self._data == bytes(other)


if __name__ == '__main__':
    def self_test():
        b = b"sensitive data"
        m = SecureMemory(b)
        print("in use:", bytes(m))
        del m
        print("freed:", b)

    self_test()
