from libc cimport stdint

cdef extern from "xsalsa20poly1305.h" nogil:
    ctypedef stdint.uint8_t u8
    ctypedef stdint.uint64_t u64
    int crypto_secretbox(u8 *ciphertext, const u8 *message, u64 d, const u8 *nonce, const u8 *key)
    int crypto_secretbox_open(u8 *message, const u8 *ciphertext, u64 d, const u8 *nonce, const u8 *key)
