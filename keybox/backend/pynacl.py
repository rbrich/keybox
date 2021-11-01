from .common import BaseArgon2Params

import nacl.pwhash
import nacl.utils
import nacl.secret


class Argon2Params(BaseArgon2Params):

    def __init__(self,
                 mem_cost: int = BaseArgon2Params.DEFAULT_MEM_COST,
                 time_cost: int = BaseArgon2Params.DEFAULT_TIME_COST,
                 threads: int = 1,
                 version: int = 0x13):
        BaseArgon2Params.__init__(self, mem_cost, time_cost, threads, version)


def argon2id(secret: bytes, salt: bytes, hash_len: int, params: Argon2Params()):
    return nacl.pwhash.argon2id.kdf(hash_len, secret, salt,
                                    params.time_cost, 2 ** (10 + params.mem_cost))


XSalsa20Poly1305 = nacl.secret.SecretBox
randombytes = nacl.utils.random
