Crypto Reference
================

This is a reference implementation of crypto functions used in Keybox.
It's not supposed to be used in production. Use PyNaCl/libsodium instead.

The module is self-contained, implemented in C and Cython.

The C functions came from:
* xsalsa20poly1305 - from TweetNaCl

References:
* [Cython](https://cython.org)
* [TweetNaCl: a crypto library in 100 tweets](https://tweetnacl.cr.yp.to/software.html)
