File Format
===========

The keybox format:

- Text format, a simple table with tab-delimited records, one per line.
- First line is a header with column names, controlling the order of columns in the file.
- Other lines are records.
- Passwords are encrypted with the same encryption as the file, encoded as BASE64.
- The whole file is compressed and encrypted (see :doc:`envelope`).

The values in the record can't contain newlines or tab characters.
Password values, on the other hand, can contain any characters, because they're encrypted
and become BASE64 strings.

Highlights:

- Documented format, easy to recover data in case this program stops working or becomes unmaintained.
- Extensibility: Should new program version need more columns, they can be
  added without breaking compatibility (both backwards and forward).
- Tab character is reserved and cannot be used in values.
- Passwords are encrypted separately, inside the file which is itself encrypted.
  This adds no security, but I feel better not having all passwords decrypted into memory every time
  I access the keybox.

Plain-text format
-----------------
Plain-text format used by import/export is similar to keybox format, but without encrypted passwords.

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


Export
------
Use export command to decrypt all data including passwords:

.. code-block:: sh

    $ keybox export --plain

This will print exported data to stdout, which can be directed to other programs.
Use ``-o`` parameter to write to a file instead.
The output can be used when migrating data to another password manager.
