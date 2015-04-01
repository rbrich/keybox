#!/usr/bin/env python3
# pwlockr.py - Secure locker for your passwords.
# Copyright 2015 Radek Brich

from pwlockr.memlock import memlock
from pwlockr.ui import DEFAULT_FILENAME
from pwlockr.shell import ShellUI
from pwlockr.batch import LockerBatch
from pwlockr.pwgen import pwgen, NUM_WORDS, NUM_SPECIAL, MIN_LENGTH

from getpass import getpass
import argparse


def cmd_shell(args):
    shell = ShellUI(args.locker_file)
    shell.start()


def cmd_gen(args):
    entropy = []
    print(pwgen(args.words, args.special, args.length, entropy=entropy))
    print("%7.2f bits of entropy (based on algorithm)\n"
          "%7.2f bits of rough entropy (based on symbol groups)"
          % tuple(entropy))


def cmd_import(args):
    passphrase = getpass('Passphrase:')
    locker = LockerBatch(args.locker_file, passphrase)
    locker.read()
    num_total, num_ok = locker.import_file(args.import_file)
    print("%d records imported (%d duplicates)."
          % (num_ok, num_total - num_ok))
    if num_ok > 0:
        locker.write()


def cmd_export(args):
    passphrase = getpass('Passphrase:')
    locker = LockerBatch(args.locker_file, passphrase)
    locker.read()
    locker.export()


def main():
    """Process command line args."""
    ap = argparse.ArgumentParser(description="password locker",
                                 formatter_class=argparse.RawTextHelpFormatter)

    ap.add_argument('command', choices=['shell', 'gen', 'import', 'export'],
                    nargs='?', default='shell',
                    help="shell: start shell (default)\n"
                         "gen: generate random password\n"
                         "import: import formatted records from stdin "
                         "or another file (see --import-file)\n"
                         "export: decrypt and export content of locker file "
                         "to stdout")

    ap.add_argument('-f', dest='locker_file', default=DEFAULT_FILENAME,
                    help="password locker file (default: %(default)s)")
    ap.add_argument('-i', dest='import_file', type=str, default=None,
                    help="import: use this file instead of stdin")
    ap.add_argument('--decrypt-passwords', action='store_true',
                    help="export: decrypt all passwords")

    # pwgen args
    ap.add_argument('-w', dest='words', type=int, default=NUM_WORDS,
                    help="gen: number of words to concatenate "
                         "(default: %(default)s)")
    ap.add_argument('-s', dest='special', type=int, default=NUM_SPECIAL,
                    help="gen: number of uppercase, digit and punctuation "
                         "symbols to add (default: %(default)s)")
    ap.add_argument('-l', dest='length', type=int, default=MIN_LENGTH,
                    help="gen: minimal length of password "
                         "(default: %(default)s)")

    args = ap.parse_args()
    globals()['cmd_' + args.command](args)


if __name__ == '__main__':
    memlock()
    main()
