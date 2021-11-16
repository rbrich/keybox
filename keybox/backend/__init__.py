from importlib import import_module

# each symbol must be provided by one of the backends
# noinspection PyUnresolvedReferences
__all__ = (
    # KDF
    'Argon2Params', 'argon2id',
    # cipher
    'XSalsa20Poly1305',
    # compression
    'noop_compress', 'noop_decompress',
    'deflate_compress', 'deflate_decompress',
    # checksum
    'crc32',
    # utility
    'randombytes',
    'SecureMemory',
    'lock_file',
    'timeout',
)

# ordered by priority, the first one providing a function will be picked
all_backend_names = ('cryptoref', 'argon2_cffi', 'pynacl', 'os_unix', 'os_windows', 'standard')

symbol_provided_by = {
    'Argon2Params': ('argon2_cffi', 'pynacl'),
    'argon2id': ('argon2_cffi', 'pynacl'),
    'XSalsa20Poly1305': ('pynacl', 'cryptoref'),
    'noop_compress': ('standard',),
    'noop_decompress': ('standard',),
    'deflate_compress': ('standard',),
    'deflate_decompress': ('standard',),
    'crc32': ('standard',),
    'randombytes': ('pynacl', 'standard'),
    'SecureMemory': ('os_unix', 'os_windows'),
    'lock_file': ('os_unix', 'os_windows'),
    'timeout': ('os_unix', 'standard'),
}

available_backends = ()
for backend_name in all_backend_names:
    try:
        available_backends += (import_module('.' + backend_name, __name__),)
    except ImportError:
        pass
del backend_name


class MissingError(RuntimeError):

    def __init__(self, msg):
        RuntimeError.__init__(self, msg)


class MissingSurrogate:

    def __init__(self, name, backends):
        self._name, self._backends = name, backends

    def _missing(self):
        raise MissingError(f"Missing {self._name}. Please install {' or '.join(self._backends)}.")

    def __getattr__(self, item):
        self._missing()

    def __call__(self, *args, **kwargs):
        self._missing()


def __getattr__(name):
    provided_by_backends = symbol_provided_by[name]
    for backend in available_backends:
        backend_name = backend.__name__.split('.')[-1]
        if backend_name in provided_by_backends:
            # print(f"Using {name} from {backend}")
            return getattr(backend, name)
    return MissingSurrogate(name, provided_by_backends)
