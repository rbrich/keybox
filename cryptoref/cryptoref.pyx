# distutils: sources = cryptoref/xsalsa20poly1305.c
# cython: language_level=3

import os
from libc.stdlib cimport malloc, free
from xsalsa20poly1305 cimport *


def xsalsa20poly1305_encrypt(bytes message, bytes nonce, bytes key):
    if len(nonce) != 24:
        raise ValueError("nonce must have 24 bytes")
    if len(key) != 32:
        raise ValueError("key must have 32 bytes")
    cdef size_t d = len(message) + 32
    cdef unsigned char *ciphertext = <unsigned char *> malloc(d)

    crypto_secretbox(ciphertext, 32*b'\0' + message, d, nonce, key)
    try:
        return ciphertext[16:d]
    finally:
        free(ciphertext)


def xsalsa20poly1305_decrypt(bytes ciphertext, bytes nonce, bytes key):
    if len(nonce) != 24:
        raise ValueError("nonce must have 24 bytes")
    if len(key) != 32:
        raise ValueError("key must have 32 bytes")
    cdef size_t d = len(ciphertext) + 16
    cdef unsigned char *message = <unsigned char *> malloc(d)

    rc = crypto_secretbox_open(message, 16*b'\0' + ciphertext, d, nonce, key)
    if rc == -1:
        raise ValueError('Failed message authentication')
    try:
        return message[32:d]
    finally:
        free(message)
