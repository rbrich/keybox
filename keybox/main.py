import sys
import argparse
import configparser
from pathlib import Path

from . import pwgen, shell, ui


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
    base_ui = ui.BaseUI(keybox_file)
    if not base_ui.open(readonly=True):
        return
    print("Searching for %r..." % filter_expr)
    base_ui.cmd_select(filter_expr)
    if not base_ui.selected:
        return
    base_ui.cmd_print()


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
    base_ui = ui.BaseUI(keybox_file)
    if not base_ui.open(readonly=True):
        return
    base_ui.cmd_export(output_file, file_format)


def run_import(config_file, keybox_file, import_file, file_format, quiet, delete):
    cfg = Config(config_file)
    keybox_file = cfg.keybox_file(override=keybox_file)
    base_ui = ui.BaseUI(keybox_file)
    if not base_ui.open():
        return
    if not base_ui.cmd_import(import_file, file_format, quiet):
        return
    base_ui.close(ask_write="Write imported changes?")
    if delete and not base_ui.keybox.modified():
        Path(import_file).unlink()
        print(f"Removed imported file {str(import_file)!r}")


def parse_args():
    """Process command line args."""
    ap = argparse.ArgumentParser(prog="keybox",
                                 description="Keybox manager",
                                 formatter_class=argparse.RawTextHelpFormatter)

    # Sub-commands
    sp = ap.add_subparsers()
    ap_shell = sp.add_parser("shell", aliases=['sh'],
                             help="start shell (default)")
    ap_shell.set_defaults(func=run_shell)
    ap_pwgen = sp.add_parser("pwgen", help="generate random password")
    ap_pwgen.set_defaults(func=run_pwgen)
    ap_export = sp.add_parser("export", help="export content of keybox file")
    ap_export.set_defaults(func=run_export)
    ap_import = sp.add_parser("import", help="import records from a file")
    ap_import.set_defaults(func=run_import, file_format='keybox_gpg')
    ap_print = sp.add_parser("print", aliases=['p'],
                             help="print key specified by pattern")
    ap_print.set_defaults(func=run_print)

    for subparser in (ap_shell, ap_import, ap_export, ap_print):
        subparser.add_argument('-c', '--config', dest='config_file',
                               default=ui.DATA_DIR / 'keybox.conf',
                               help="keybox file (default: %(default)s)")
        subparser.add_argument('-f', dest='keybox_file',
                               help=f"keybox file (default: {shell.ShellUI.get_default_filename()})")

    ap_shell.add_argument('-r', dest="readonly", action='store_true',
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

    ap_print.add_argument('filter_expr',
                          help="Expression for selecting record to be printed. "
                               "Format is [<column>:]<text>. "
                               "Default <column> is 'site,url'. ")

    args = ap.parse_args()

    if 'func' not in args:
        ap_shell.parse_args(namespace=args)

    return args


def main():
    args = parse_args()
    run_func = args.func
    delattr(args, 'func')
    run_func(**vars(args))
