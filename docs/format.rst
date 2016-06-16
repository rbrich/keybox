File Format
===========

Description:

- Text format, simple table, <tab> delimited.
- First row is header with column names.
- Other rows are records.
- Passwords are encrypted with master password (see bellow).
- Whole file is encrypted with master password (see bellow).

Features:

- Easy recovery, in case this program stops working or becomes unmaintained.
- Extensibility: Should new program version need more columns, they can be
  added without breaking compatibility (both backwards and forward).
- Tab character is reserved and cannot be used in values.
- Passwords are encrypted inside the whole encrypted file. This adds no security,
  but I feel better not having all passwords decrypted into memory every time
  I access the keybox.

Import
------
Batch import of passwords is supported via command line.

- Format the data into tab-delimited file with header.
- Header should contain subset or all of :data:`keys.record.COLUMNS`.
- Rest of lines should contain records with data according to header.

Example import file::

    site	user	password
    Example	johny	pa$$w0rD
    Other site	j.x	SLevel6

Write this to import.recs (be sure to use TAB characters between data)
and import the file:

.. code-block:: sh

    $ # Import file
    $ keys import -i import.recs
    $ # Import output from other program
    $ cat import.recs | keys import

How to create keybox file using standard tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This recipe shows how to create new file with single record:

.. code-block:: sh

    $ # Master passphrase
    $ MASTER='secret'
    $ # Passwords are encrypted and encoded as BASE64
    $ PASSWORD=$(printf "paSSw0rD" | gpg --passphrase $MASTER --symmetric \
                 --cipher-algo AES256 | base64 -w0)
    $ # Format and encrypt the file
    $ printf "site\tuser\tpassword\nExample\tjohny\t$PASSWORD\n" | gpg \
        --passphrase $MASTER --output pw.gpg --symmetric --cipher-algo AES256


Export
------
Use export function to decrypt all data including passwords:

.. code-block:: sh

    $ keys export

This will print exported data to stdout, which can be directed to other
programs. This is useful for conversion to other formats.

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
