#ifndef XSALSA20POLY1305_H
#define XSALSA20POLY1305_H

#include <stdint.h>

typedef uint8_t u8;
typedef uint64_t u64;

#define crypto_secretbox_PRIMITIVE "xsalsa20poly1305"
#define crypto_secretbox_KEYBYTES 32
#define crypto_secretbox_NONCEBYTES 24
#define crypto_secretbox_ZEROBYTES 32
#define crypto_secretbox_BOXZEROBYTES 16

int crypto_secretbox(u8 *ciphertext, const u8 *message, u64 d, const u8 *nonce, const u8 *key);
int crypto_secretbox_open(u8 *message, const u8 *ciphertext, u64 d, const u8 *nonce, const u8 *key);

#endif
