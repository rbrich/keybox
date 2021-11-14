from ctypes import windll, cdll, c_void_p, c_size_t, c_int
import sys


err_hint = \
    "(lookup the error code in " \
    "https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes)"


def memory_lock(addr, len):
    """Try to lock an address against being swapped.

    Encountering error while locking memory is not considered fatal,
    no exception is raised.

    The memory page is locked until the process terminates.
    Note that calls to VirtualLock do not stack, so a constructor/destructor
    pattern in SecureMemory would not work if we called VirtualUnlock.
    It would unlock the memory even when another instance wanted to keep
    it locked.

    """
    try:
        ok = windll.kernel32.VirtualLock(c_void_p(addr), c_size_t(len))
    except OSError as e:
        print("Warning: Unable to lock memory.", str(e))
        return
    if not ok:  # pragma: no cover
        err = windll.kernel32.GetLastError()
        print("Error (VirtualLock):", err, err_hint)


def memory_clear(addr, len):
    try:
        cdll.msvcrt.memset(c_void_p(addr), c_int(0), c_size_t(len))
    except OSError as e:
        print("Warning: Unable to clear memory.", str(e))
        return


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


def lock_file(_fileobj):
    # not implemented, possibly not needed (TODO: test concurrent processes)
    pass


if __name__ == '__main__':
    def self_test():
        b = b"sensitive data"
        m = SecureMemory(b)
        print("in use:", bytes(m))
        del m
        print("freed:", b)

    self_test()
