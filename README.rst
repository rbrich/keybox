=========================
Password Locker (pwlockr)
=========================

Introduction
------------

Pwlockr is a program built around simple file format. The file is encrypted
using strong encryption. Unlike most password managers, this is completely
offline. All your secrets stay safe in local file. Nothing is sent anywhere,
unless you explicitly set up network synchronization using some other tool.

Features:

- Shell-like text user interface
- Data encrypted with GPG
- Simple tab-delimited file format

Security:

- Master password is saved in memory for as long as the program runs.
- Neither the password nor decrypted data are ever written to disk.

Portability:

- The script should run on any system with Python3 and GPG installed.
- Requires no installation. You can bring your password locker with you anywhere.
- Can be contained in single Python file (see Distribution_ bellow)

Dependencies:

- POSIX OS
- GPG
- Python 3.2 or later (Python 3.3 recommended)


Getting Started
^^^^^^^^^^^^^^^

Run the program, type master password. New locker file will be created.

You are now in the shell. The basic workflow is as follows:

- **add** some passwords
- **list** the records
- **select** a record
- **print** the password
- **quit**

See **help** for list of all commands.


Password Generator
^^^^^^^^^^^^^^^^^^

Bundled password generator can be called from command line (``./pwlockr.py gen``)
or internally from shell. Try ``add user <tab>``.

Pwgen is based on system word list usually found in ``/usr/share/dict/words``.
By default, it makes password from two words concatenated with an underline
and two random characters inserted at random places.

This gives around 50 bits of entropy on my system. [#wiki]_

See :mod:`pwlockr.pwgen` for more information.

.. [#wiki] http://en.wikipedia.org/wiki/Password_strength


Distribution
^^^^^^^^^^^^

Call ``make`` to combine all sources into single Python script.
Distributable script will be created in ``dist`` directory.
Put it next to your password file.

Additional requirement for Python 3.2 is ``funcsigs`` package.
It can be installed from pypy (``pip3 install funcsigs``).
Call ``make static32`` to also embed funcsigs source into pwlockr
distributable script (funcsigs package must be installed prior to that).

Nicer alternative for static script is zipapp format. [#zipapp]_

Call ``make zipapp33`` to create ``pwlockr-py33.pyz`` executable
in ``dist`` directory.

.. [#zipapp] https://docs.python.org/3.5/library/zipapp.html#the-python-zip-application-archive-format
