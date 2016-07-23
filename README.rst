====
Keys
====

Introduction
------------

Keys is a Python package with utilities for managing your passwords, keys
and other secrets. It can be used directly from Python (``import keys``) or
run as program (``python3 -m keys``, or just ``keys``).

Unlike most password managers, this is completely offline. All your secrets
stay safe in local file. Nothing is sent anywhere, unless you explicitly
set up network synchronization using some other tool.

Features:

- Data encrypted using strong encryption (GPG file)
- Simple tab-delimited file format
- Shell-like text user interface

Security:

- Master password is saved in memory for as long as the program runs.
- Neither the password nor decrypted data are ever written to disk.

Portability:

- The script should run on any system with Python3 and GPG installed.
- Requires no installation. You can bring your keys with you anywhere.
- Can be contained in single Python file (see `Static Distribution`_ bellow)

Dependencies:

- POSIX OS
- GPG
- Python 3.3 or later


Installation
^^^^^^^^^^^^

Install Python package together with ``keys`` script::

    python3 setup.py install

The package can also be run directly::

    python3 -m keys


Getting Started
^^^^^^^^^^^^^^^

Run the program, type master password. New keybox file will be created.

You are now in the shell. The basic workflow is as follows:

- **add** some passwords
- **list** the records
- **select** a record
- **print** the password
- **quit**

See **help** for list of all commands.


Password Generator
^^^^^^^^^^^^^^^^^^

Bundled password generator can be called from command line (``keys pwgen``)
or internally from shell. Try ``<tab>`` when asked for password (add command).

Pwgen is based on system word list usually found in ``/usr/share/dict/words``.
By default, it makes password from two concatenated words, one uppercase letter,
one digit and one punctuation character.

This gives around 50 bits of entropy on my system. [#wiki]_

.. [#wiki] http://en.wikipedia.org/wiki/Password_strength


Static Distribution
^^^^^^^^^^^^^^^^^^^

Call ``make zipapp`` to create [#zipapp]_ file containing all sources.
Zipapp file is written to ``dist`` directory and is directly executable
by Python.

The make target uses ``zipapp`` module which is available since Python 3.5.
When created, the zipapp archive is executable by Python 3.3.

.. [#zipapp] https://docs.python.org/3.5/library/zipapp.html#the-python-zip-application-archive-format


Development
^^^^^^^^^^^

Run tests::

    make test

Show test code coverage::

    make htmlcov

.. image:: https://travis-ci.org/rbrich/keys.svg?branch=master
    :target: https://travis-ci.org/rbrich/keys
