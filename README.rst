======
Keybox
======

Introduction
------------

Keybox is a secure store for passwords, keys, and other secrets.

There is a Python API (``import keybox``), a runnable package (``python3 -m keybox``)
and a wrapper script (``keybox``, created by setuptools).

Keybox is completely offline. All secrets stay safely in a local file.
Nothing is sent anywhere, unless you explicitly set up network synchronization
using some other tool.

Features:

- Data encrypted using strong encryption (PyNaCl)
- Inside encrypted envelope, it's a simple tab-delimited file format
- Shell-like text user interface

Security:

- Master password is saved in memory for as long as the program runs.
- Neither the password nor decrypted data are written to the disk (unless explicitly exported).

Portability:

- The script should run on any system with Python3 installed (including Windows).
- Requires no installation. You can bring your keybox with you anywhere.
- Can be contained in a single Python file (see `Static Distribution`_ below)

Dependencies:

- Python 3.7 or later
- PyNaCl, prompt_toolkit, blessed, pyperclip


Installation
------------

Install Python package, together with the ``keybox`` wrapper script,
from PyPI::

    pip3 install keybox

That's it. PIP should pull in the required dependencies.

From source / Git repo
``````````````````````

Alternatively, install from source::

    python3 setup.py install

The package can also run without installation, directly from source tree root::

    python3 -m keybox

Dependencies
````````````

* `pynacl <https://pynacl.readthedocs.io/en/latest/install/>`_ - the encryption

* **argon2-cffi** - optional, replaces argon2 from PyNaCl when available

* **prompt_toolkit, blessed, pyperclip** - command-line and shell

*  ``/usr/share/dict/words``

   * used for password generator
   * Debian: ``apt install wamerican``
   * when not available, a replacement ``words`` file is downloaded from Internet
     (This is the only option on Windows)

* **pytest, coverage** - for tests

Getting Started
---------------

Run the program, choose a master password. A new keybox file will be created.

You are now in the shell. The basic workflow uses the following commands:

- **add** some passwords
- **list** the records
- **select** a record
- **print** the password
- **quit**

Type **help** for a list of all commands, **help <cmd>** for description of each command and its parameters.


Config file
-----------

The default config file path is ``~/.keybox/keybox.conf``.
It can be used to point to a different location for the keybox file::

    [keybox]
    path = ~/vcs/keybox/keybox.safe

Without the config file, the default keybox path is ``~/.keybox/keybox.safe``.


Password Generator
------------------

A bundled password generator can be called from command line (``keybox pwgen``)
or internally from the shell.
In the shell, use ``<tab>`` when asked for a password (in the ``add``/``modify`` commands)
to generate some random passwords.

Pwgen is based on the system word list that is usually found in ``/usr/share/dict/words``.
By default, it generates a password from two concatenated words, altered by
adding two uppercase letters and one digit somewhere inside the password.

This gives around 50 bits of entropy on my system
(`Password strength <http://en.wikipedia.org/wiki/Password_strength>`_).


Static Distribution
-------------------

Call ``make zipapp`` to create a `zipapp file <https://docs.python.org/3.5/library/zipapp.html#the-python-zip-application-archive-format>`_ containing all sources.
The zipapp file is written to ``build`` directory and is directly executable
by Python.

The Makefile target uses ``zipapp`` module which is available since Python 3.5.


Development
-----------

Build docs::

    make -C docs html

Run tests::

    make test

Show test code coverage::

    make htmlcov

Build and check package::

    make build
    make check


The Project Name
----------------

There might be some confusion between this Keybox project and GnuPG project,
which has something called "a keybox file (.kbx)" and a tool to handle it,
`kbxutil <https://www.gnupg.org/documentation/manuals/gnupg/kbxutil.html>`_.

This Keybox is completely unrelated to the GnuPG one.
