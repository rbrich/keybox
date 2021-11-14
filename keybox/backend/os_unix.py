import ctypes
from ctypes.util import find_library
from ctypes import c_void_p, c_size_t, c_int
import sys
import os
import errno
import resource
import fcntl
import signal
from contextlib import contextmanager

libc = ctypes.CDLL(find_library("c"), use_errno=True)


def memory_lock(addr, len):
    """Try to lock an address against being swapped.

    Encountering error while locking memory is not considered fatal,
    no exception is raised.

    The memory page is locked until the process terminates.
    We cannot pair mlock/munlock safely without additional page management.
    From linux' mlock(2):
    > Memory locks do not stack, that is, pages which have been locked several times
    > by calls to mlock() or mlockall() will be unlocked by a single call to munlock()
    > for the corresponding range.

    """
    # Set MEMLOCK soft limit to maximum
    limits = resource.getrlimit(resource.RLIMIT_MEMLOCK)
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (limits[1], limits[1]))
    try:
        rc = libc.mlock(c_void_p(addr), c_size_t(len))
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


def memory_clear(addr, len):
    try:
        rc = libc.memset(c_void_p(addr), c_int(0), c_size_t(len))
    except OSError as e:
        print("Warning: Unable to clear memory.", str(e))
        return
    if rc == -1:  # pragma: no cover
        err = ctypes.get_errno()
        print("Error (memset):", errno.errorcode[err], os.strerror(err))


class SecureMemory:

    """Memlock the memory (do not allow swap).

    Zero the memory in deleter. This is a little hacky,
    it depends on CPython and its bytes object implementation.

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

    def __bytes__(self):
        return self._data

    def __eq__(self, other):
        return self._data == bytes(other)


def lock_file(fileobj):
    fcntl.lockf(fileobj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


@contextmanager
def timeout(secs: int, handler):
    def sigalrm_handler(_signum, _frame):
        handler()
    orig_handler = signal.signal(signal.SIGALRM, sigalrm_handler)
    signal.alarm(int(secs))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, orig_handler)


if __name__ == '__main__':
    def self_test():
        b = b"sensitive data"
        m = SecureMemory(b)
        print("in use:", bytes(m))
        del m
        print("freed:", b)

    self_test()
