import sys
import argparse
import configparser
from pathlib import Path

from . import pwgen, shell, ui, datasafe, backend


class Config:

    def __init__(self, config_file):
        self._keybox_file = None
        self.load(config_file)

    def load(self, config_file):
        config_file = Path(config_file).expanduser()
        print(f'Loading config {str(config_file)!r}...')
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        for section in config.sections():
            if section != 'keybox':
                print(f"WARNING: unknown section {section!r} in config {config_file!r}")
                continue
            section = config[section]
            for key in section:
                if key == 'path':
                    self._keybox_file = Path(section[key])
                else:
                    print(f"WARNING: unknown key [{section.name!r}] {key!r} in config {config_file!r}")
                    continue

    def keybox_file(self, override=None):
        if override is not None:
            return Path(override)
        return self._keybox_file or shell.ShellUI.get_default_filename()


def run_print(config_file, keybox_file, filter_expr):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    base_ui = ui.KeyboxUI(keybox_file)
    if not base_ui.open(readonly=True):
        return
    print("Searching for %r..." % filter_expr)
    base_ui.cmd_select(filter_expr)
    if not base_ui.selected:
        return
    base_ui.cmd_print()


def run_copy(config_file, keybox_file, filter_expr):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    base_ui = ui.KeyboxUI(keybox_file)
    if not base_ui.open(readonly=True):
        return
    print("Searching for %r..." % filter_expr)
    base_ui.cmd_select(filter_expr)
    if not base_ui.selected:
        return
    base_ui.cmd_copy()


def run_shell(config_file, keybox_file, readonly, timeout):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    filename_gpg = keybox_file.expanduser().with_suffix('.gpg')
    if filename_gpg.exists():
        print(f"Found old-format file. To convert it, reply 'n' and run:")
        print()
        print(f"    {sys.executable} -m keybox import -q --delete {str(filename_gpg)!r}")
        print()

    shell.SHELL_TIMEOUT_SECS = timeout
    shell_ui = shell.ShellUI(keybox_file)
    shell_ui.start(readonly)


def run_pwgen(length, words, upper, digits, special):
    for _ in range(10):
        print(pwgen.generate_password(length),
              pwgen.generate_passphrase(words, length, upper, digits, special),
              sep='   ')


def run_export(config_file, keybox_file, output_file, file_format):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    base_ui = ui.KeyboxUI(keybox_file)
    if not base_ui.open(readonly=True):
        return
    base_ui.cmd_export(output_file, file_format)


def run_import(config_file, keybox_file, import_file, file_format, quiet, delete):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    base_ui = ui.KeyboxUI(keybox_file)
    if not base_ui.open():
        return
    if not base_ui.cmd_import(import_file, file_format, quiet):
        return
    base_ui.close(ask_write="Write imported changes?")
    if delete and not base_ui.keybox.modified():
        Path(import_file).unlink()
        print(f"Removed imported file {str(import_file)!r}")


def run_encrypt(file, keep):
    plain_file = Path(file).expanduser()
    safe_file = plain_file.with_suffix(plain_file.suffix + '.safe')
    safe_ui = datasafe.DataSafeUI(safe_file)
    if not safe_ui.create():
        return
    safe_ui.encrypt_file(plain_file)
    safe_ui.close()
    if not keep:
        plain_file.unlink()
        print(f"Removed original file {str(plain_file)!r}")


def run_decrypt(file, keep):
    safe_file = Path(file).expanduser()
    plain_file = safe_file.with_suffix('')
    safe_ui = datasafe.DataSafeUI(safe_file)
    if not safe_ui.open():
        return
    if not safe_ui.decrypt_file(plain_file):
        return
    safe_ui.close(unlink=(not keep))


def parse_args(argv=None):
    """Process command line args."""
    ap = argparse.ArgumentParser(prog="keybox",
                                 description="Keybox manager",
                                 formatter_class=argparse.RawTextHelpFormatter)

    # Sub-commands
    sp = ap.add_subparsers()
    ap_shell = sp.add_parser("shell", aliases=['sh'],
                             help="start shell (default)")
    ap_shell.set_defaults(func=run_shell)
    ap_pwgen = sp.add_parser("pwgen", help="generate some random passwords")
    ap_pwgen.set_defaults(func=run_pwgen)
    ap_export = sp.add_parser("export", help="export content of keybox file")
    ap_export.set_defaults(func=run_export, file_format='plain')
    ap_import = sp.add_parser("import", help="import records from a file")
    ap_import.set_defaults(func=run_import, file_format='keybox')
    ap_print = sp.add_parser("print", aliases=['p'],
                             help="search for a record by pattern and print the password")
    ap_print.set_defaults(func=run_print)
    ap_copy = sp.add_parser("copy", aliases=['c'],
                            help="search for a record by pattern and "
                                 "copy the password to clipboard")
    ap_copy.set_defaults(func=run_copy)

    ap_encrypt = sp.add_parser("encrypt", aliases=['enc'], help="encrypt a file (.safe format)")
    ap_encrypt.set_defaults(func=run_encrypt)
    ap_decrypt = sp.add_parser("decrypt", aliases=['dec'], help="decrypt a file (.safe format)")
    ap_decrypt.set_defaults(func=run_decrypt)

    for subparser in (ap_encrypt, ap_decrypt):
        subparser.add_argument('file', type=str,
                               help="a file to be encrypted/decrypted")
        subparser.add_argument('-k', '--keep', action='store_true',
                               help="keep the original file after successful encryption/decryption")

    for subparser in (ap_shell, ap_import, ap_export, ap_print, ap_copy):
        subparser.add_argument('-c', '--config', dest='config_file',
                               default=ui.DATA_DIR / 'keybox.conf',
                               help="keybox file (default: %(default)s)")
        subparser.add_argument('-f', dest='keybox_file',
                               help=f"keybox file (default: {shell.ShellUI.get_default_filename()})")

    ap_shell.add_argument('-r', '--read-only', dest="readonly", action='store_true',
                          help="open keybox in read-only mode")
    ap_shell.add_argument('--timeout', type=int, default=shell.SHELL_TIMEOUT_SECS,
                          help="Save and quit when timeout expires "
                               "(default: %(default)s)")

    ap_import.add_argument('import_file', type=str,
                           help="the file to be imported ('-' for stdin)")
    ap_import.add_argument('-q', '--quiet', action='store_true',
                           help="do not print new records (use when importing to empty keybox)")
    ap_import.add_argument('-D', '--delete', action='store_true',
                           help="unlink imported file on success")
    ap_export.add_argument('-o', dest='output_file', type=str, default='-',
                           help="use this file instead of stdout")
    for subparser in (ap_import, ap_export):
        format_grp = subparser.add_mutually_exclusive_group(required=(subparser == ap_export))
        format_grp.add_argument('--plain', dest='file_format', action='store_const', const='plain',
                                help="select plain-text format")
        format_grp.add_argument('--json', dest='file_format', action='store_const', const='json',
                                help="select JSON format")
        if subparser == ap_import:
            format_grp.add_argument('--gpg', dest='file_format', action='store_const', const='keybox_gpg',
                                    help="select legacy GPG format")

    ap_pwgen.add_argument('-l', dest='length', type=int, default=pwgen.MIN_LENGTH,
                          help="pwgen: minimal length of password "
                               "(default: %(default)s)")
    ap_pwgen.add_argument('-w', dest='words', type=int, default=pwgen.NUM_WORDS,
                          help="pwgen: number of words to concatenate "
                               "(default: %(default)s)")
    ap_pwgen.add_argument('-u', dest='upper', type=int, default=pwgen.NUM_UPPER,
                          help="pwgen: number of letters to make uppercase "
                               "(default: %(default)s)")
    ap_pwgen.add_argument('-d', dest='digits', type=int, default=pwgen.NUM_DIGITS,
                          help="pwgen: number of digits to add "
                               "(default: %(default)s)")
    ap_pwgen.add_argument('-s', dest='special', type=int, default=pwgen.NUM_SPECIAL,
                          help="pwgen: number of special symbols to add "
                               "(default: %(default)s)")

    for subparser in (ap_print, ap_copy):
        subparser.add_argument('filter_expr',
                               help="Expression for selecting record to be printed. "
                                    "Format is [<column>:]<text>. "
                                    "Default <column> is 'site,url'. ")

    args = ap.parse_args(args=argv)

    if 'func' not in args:
        ap_shell.parse_args(namespace=args)

    return args


def main(argv=None):
    """Main program

    :param argv: Used in tests. Default is sys.argv
    :return: None
    """
    args = parse_args(argv)
    run_func = args.func
    delattr(args, 'func')
    try:
        run_func(**vars(args))
    except backend.MissingError as e:
        print(e)
