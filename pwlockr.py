#!/usr/bin/env python3
# pwlockr.py - Secure locker for your passwords.
# Copyright 2015 Radek Brich

from getpass import getpass
import argparse
import fcntl
import os

from pwlockr.memlock import memlock
from pwlockr.ui import DEFAULT_FILENAME
from pwlockr.shell import ShellUI
from pwlockr.batch import LockerBatch
from pwlockr import pwgen


def cmd_shell(args):
    memlock()
    shell = ShellUI(args.locker_file)
    shell.start(args.readonly)


def cmd_gen(args):
    for _ in range(10):
        print(pwgen.generate_password(args.length),
              pwgen.generate_passphrase(args.words, args.length,
                                        args.upper, args.digits, args.special),
              sep='   ')


def cmd_import(args):
    passphrase = getpass('Passphrase:')
    locker = LockerBatch(passphrase)
    with open(args.locker_file, 'rb') as f:
        locker.read(f)
    num_total, num_ok = locker.import_file(args.import_file)
    print("%d records imported (%d duplicates)."
          % (num_ok, num_total - num_ok))
    if num_ok > 0:
        filename_tmp = args.locker_file + '.tmp'
        with open(filename_tmp, 'wb') as f:
            fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locker.write(f)
            os.rename(filename_tmp, args.locker_file)


def cmd_export(args):
    passphrase = getpass('Passphrase:')
    locker = LockerBatch(passphrase)
    with open(args.locker_file, 'rb') as f:
        locker.read(f)
    locker.export_file(args.export_file)


def main():
    """Process command line args."""
    ap = argparse.ArgumentParser(description="password locker",
                                 formatter_class=argparse.RawTextHelpFormatter)

    ap.add_argument('command', choices=['shell', 'gen', 'import', 'export'],
                    nargs='?', default='shell',
                    help="shell: start shell (default)\n"
                         "gen: generate random password\n"
                         "import: import formatted records from stdin "
                         "or another file (-i <file>)\n"
                         "export: decrypt and export content of locker file "
                         "to stdout")

    ap.add_argument('-f', dest='locker_file', default=DEFAULT_FILENAME,
                    help="password locker file (default: %(default)s)")
    ap.add_argument('-r', dest="readonly", action="store_true",
                    help="open locker in read-only mode")
    ap.add_argument('-i', dest='import_file', type=str, default='-',
                    help="import: use this file instead of stdin")
    ap.add_argument('-o', dest='export_file', type=str, default='-',
                    help="export: use this file instead of stdout")

    # pwgen args
    ap.add_argument('-l', dest='length', type=int, default=pwgen.MIN_LENGTH,
                    help="gen: minimal length of password "
                         "(default: %(default)s)")
    ap.add_argument('-w', dest='words', type=int, default=pwgen.NUM_WORDS,
                    help="gen: number of words to concatenate "
                         "(default: %(default)s)")
    ap.add_argument('-u', dest='upper', type=int, default=pwgen.NUM_UPPER,
                    help="gen: number of letters to make uppercase "
                         "(default: %(default)s)")
    ap.add_argument('-d', dest='digits', type=int, default=pwgen.NUM_DIGITS,
                    help="gen: number of digits to add "
                         "(default: %(default)s)")
    ap.add_argument('-s', dest='special', type=int, default=pwgen.NUM_SPECIAL,
                    help="gen: number of special symbols to add "
                         "(default: %(default)s)")

    args = ap.parse_args()
    globals()['cmd_' + args.command](args)


if __name__ == u'__main__':
    main()
