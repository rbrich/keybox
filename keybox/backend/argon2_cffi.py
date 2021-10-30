from .common import BaseArgon2Params

from argon2.low_level import hash_secret_raw, Type, ARGON2_VERSION


class Argon2Params(BaseArgon2Params):

    def __init__(self,
                 mem_cost: int = BaseArgon2Params.DEFAULT_MEM_COST,
                 time_cost: int = BaseArgon2Params.DEFAULT_TIME_COST,
                 threads: int = 1,  # must be 1 for compatibility with libsodium
                 version: int = ARGON2_VERSION):
        BaseArgon2Params.__init__(self, mem_cost, time_cost, threads, version)


def argon2id(secret: bytes, salt: bytes, hash_len: int, params: Argon2Params()):
    return hash_secret_raw(secret, salt,
                           params.time_cost, 2 ** params.mem_cost,
                           params.threads, hash_len, Type.ID, params.version)
