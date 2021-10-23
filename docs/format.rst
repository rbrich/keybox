File Format
===========

The keybox format:

- Text format, a simple table with tab-delimited records, one per line.
- First line is a header with column names, controlling the order of columns in the file.
- Other lines are records.
- Passwords are encrypted with master password (``gpg --symmetric --cipher-algo AES256 | base64 -w0``).
- The whole file is encrypted with master password (``gpg --symmetric --cipher-algo AES256``).

The values in the record can't contain newlines or tab characters.
Password values, on the other hand, can contain any characters, because they're encrypted
and become BASE64 strings.

Highlights:

- Easy recovery, in case this program stops working or becomes unmaintained.
- Extensibility: Should new program version need more columns, they can be
  added without breaking compatibility (both backwards and forward).
- Tab character is reserved and cannot be used in values.
- Passwords are encrypted separately, inside the file which is itself encrypted.
  This adds no security, but I feel better not having all passwords decrypted into memory every time
  I access the keybox.

Plain-text format
-----------------
Plain-text format used by import/export is similar to keybox format, but without encryption.

The format is tab-delimited table with a header:

- Header should contain subset or all of :data:`keybox.record.COLUMNS`.
- The rest of lines should contain records with columns ordered according to the header.
- All columns except password are verbatim and they can't contain newlines or tabs.
- Passwords are C-escaped, i.e. newline becomes '\n', tab becomes '\t', backslash becomes '\\'.

Example::

    site	user	password
    Example	johny	pa$$w0rD
    Other site	j.x	SLevel6

JSON format
-----------
JSON format used by import/export. It's an array of objects::

    [
        {
            "site": "Example",
            "user": "johny",
            "password": "pa$$w0rD"
        },
        {
            "site": "Other site",
            "user": "j.x",
            "password": "SLevel6"
        }
    ]

Supported columns
-----------------
The columns recognized by all formats (keybox, plain-text, json) are:

**site**
    short description of the record, e.g. ``"Exa Ample"``
**user**
    username, e.g. ``"user@example.com"``
**url**
    full URL, e.g. ``"https://example.com"``
**tags**
    space-delimited list of tags, e.g. ``"e-shop free_time"`` (a tag can't contain spaces)
**mtime**
    last modification, ISO timestamp, e.g ``"2015-03-29 11:48:38"`` (UTC time)
**note**
    single-line note
**password**
    the secret, can contain any characters including newlines


Import
------
Import records from another keybox, plain-text format, or JSON format.

Having plain-text records written in ``import.recs`` file (see above),
you can import them:

.. code-block:: sh

    $ # Import file
    $ keybox import --plain import.recs
    $ # Import output from other program
    $ cat import.recs | keybox import --plain -

Note that the default format (without --plain) is the keybox format.
The third option is --json.

How to create keybox file using standard tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Instead of the import command, the keybox file can be created directly by other programs.
The following example shows how to create it using standard tools in Bash:

.. code-block:: sh

    $ # Master passphrase
    $ MASTER='secret'
    $ # Passwords are encrypted and encoded as BASE64
    $ PASSWORD=$(printf "paSSw0rD" | gpg --passphrase $MASTER --symmetric \
                 --cipher-algo AES256 | base64 -w0)
    $ # Format and encrypt the file
    $ printf "site\tuser\tpassword\nExample\tjohny\t${PASSWORD}\n" | gpg \
        --passphrase ${MASTER} --output pw.gpg --symmetric --cipher-algo AES256


Export
------
Use export command to decrypt all data including passwords:

.. code-block:: sh

    $ keybox export --plain

This will print exported data to stdout, which can be directed to other programs.
Use ``-o`` parameter to write to a file instead.
The output can be used when migrating data to another password manager.

How to decrypt keybox file using standard tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This recipe shows how to decrypt *pw.gpg* file created before:

.. code-block:: sh

    $ # Decrypt contents of file
    $ gpg -dq pw.gpg
    site    user    password
    Example johny   jA0E<shortened>wOQr
    $ # Passwords are encrypted and encoded as BASE64
    $ printf "jA0E<shortened>wOQr" | base64 -d | gpg -dq
    paSSw0rD
