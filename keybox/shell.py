# ShellUI
# (shell-like user interface)
#

import readline
import textwrap
import signal
import sys
from inspect import signature

from keybox.ui import BaseUI
from keybox import pwgen

SHELL_TIMEOUT_SECS = 3600  # 1 hour


def not_implemented(f):
    """Decorator for unimplemented methods.

    The function is effectively removed (set to None).

    """
    return


class BaseCompleter:

    def __init__(self, history: list=None, delims=' '):
        self._prompt = ''
        self._history = history or []
        self._delims = delims

    def input(self, prompt):
        """Input with completion and history."""
        self._prompt = prompt
        self._reset()
        self._load_history()
        value = input(prompt)
        self._save_history()
        return value

    def _reset(self):
        readline.parse_and_bind('TAB: complete')
        readline.set_completer(self._complete)
        readline.set_completer_delims(self._delims)
        readline.set_completion_display_matches_hook(self._display_matches)

    def _complete(self, text, state):
        return

    @not_implemented
    def _display_matches(self, substitution, matches, longest_match_length):
        """Override this for custom matches display"""

    def _load_history(self):
        """Restore readline history to last state."""
        readline.clear_history()
        # noinspection PyTypeChecker
        for item in self._history:
            readline.add_history(item)

    def _save_history(self):
        """Save and clear current readline history."""
        # noinspection PyArgumentList
        self._history = [readline.get_history_item(i + 1)
                         for i in range(readline.get_current_history_length())]


class ShellCompleter(BaseCompleter):

    def __init__(self, keybox, filter_commands):
        BaseCompleter.__init__(self)
        self._keybox = keybox
        self._filter_commands = filter_commands
        self._candidates = []

    def _complete(self, text, state):
        """Tab completion for readline."""
        if state == 0:
            line = readline.get_line_buffer()
            begin = readline.get_begidx()
            end = readline.get_endidx()
            to_complete = line[begin:end]
            assert to_complete == text
            completed_parts = line[:begin].split()

            if begin == 0:
                self._candidates = self._filter_commands(text)
            else:
                cmd = completed_parts[0]
                cmd = self._filter_commands(cmd)[0]
                func = getattr(self, '_complete_' + cmd, lambda p, t: [])
                self._candidates = func(completed_parts, text)
        try:
            return self._candidates[state]
        except IndexError:
            return None

    def _complete_modify(self, completed_parts, text):
        """Complete cmd_modify args."""
        if len(completed_parts) == 1:
            return self._keybox.get_columns(text)
        elif len(completed_parts) == 2:
            candidates = self._keybox.get_columns(completed_parts[1])
            if len(candidates) != 1:
                return []
            column = candidates[0]
            if column == 'password':
                return [pwgen.generate_passphrase()]
            return []
        else:
            return []


class UserCompleter(BaseCompleter):

    def __init__(self, keybox):
        BaseCompleter.__init__(self)
        self._keybox = keybox
        self._candidates = []

    def _complete(self, text, state):
        if state == 0:
            self._candidates = self._keybox.get_column_values('user', text)
        try:
            return self._candidates[state]
        except IndexError:
            return None


class PasswordCompleter(BaseCompleter):

    def __init__(self):
        BaseCompleter.__init__(self, delims='')
        self._passwords = []
        self._candidates = []

    def _complete(self, text, state):
        if state == 0:
            if text:
                # Replace the shortcut with password from generated list
                if len(text) == 1 and '0' <= text <= '9':
                    self._candidates = [self._passwords[int(text)]]
                elif len(text) == 1 and 'a' <= text <= 'j':
                    self._candidates = [self._passwords[ord(text) - ord('a') + 10]]
                else:
                    self._candidates = []
            else:
                # Fill password list
                self._passwords = [pwgen.generate_password() for _ in range(10)] + \
                                  [pwgen.generate_passphrase() for _ in range(10)]
                # Display passwords with shortcuts as candidates
                self._candidates = ["%s: %s" % (n if n < 10 else chr(ord('a') + n - 10), p)
                                    for n, p in enumerate(self._passwords)]
        try:
            return self._candidates[state]
        except IndexError:
            return None

    def _display_matches(self, substitution, matches, longest_match_length):
        print()
        half = len(matches) // 2
        for match1, match2 in zip(matches[:half], matches[half:]):
            print(match1, ' ', match2)
        print(self._prompt, readline.get_line_buffer(), sep='', end='')
        sys.stdout.flush()


class UrlCompleter(BaseCompleter):

    def __init__(self):
        BaseCompleter.__init__(self,
                               delims='', history=['https://', 'http://'])

    def _complete(self, text, state):
        if not len(text):
            candidates = ['http://']
        elif all(c.isalpha() for c in text):
            candidates = [text + '://']
        else:
            candidates = []
        try:
            return candidates[state]
        except IndexError:
            return None


class TagsCompleter(BaseCompleter):

    def __init__(self, keybox):
        BaseCompleter.__init__(self)
        self._keybox = keybox
        self._candidates = []

    def _complete(self, text, state):
        if state == 0:
            self._candidates = self._keybox.get_tags(text)
        try:
            return self._candidates[state]
        except IndexError:
            return None


class ShellUI(BaseUI):

    """Shell allows user type and execute commands.

    Uses readline for tab-completion and history.

    The entry point is :meth:`start`.

    """

    def __init__(self, filename=None):
        super().__init__(filename)
        self._commands = []
        self._command_map = {}  # name: (func, params)
        self._fill_commands()
        self._quit = False
        self._write_on_quit = True

        def sighup_handler(signum, frame):
            self.close()
        signal.signal(signal.SIGHUP, sighup_handler)

        def sigalrm_handler(signum, frame):
            raise TimeoutError
        signal.signal(signal.SIGALRM, sigalrm_handler)

    def start(self, readonly=False):
        """Start the shell. Returns when done."""
        if not self.open(readonly):
            return
        try:
            self.mainloop()
        except (KeyboardInterrupt, EOFError):
            # Ctrl-C, Ctrl-D
            print("quit")
        except TimeoutError:
            print("quit\nTimeout after %s seconds." % SHELL_TIMEOUT_SECS)
        finally:
            self.close(write=self._write_on_quit)

    def mainloop(self):
        """The main loop.

        `open` must be called before this and `close` should be called after.
        See `start`.

        """
        completer = ShellCompleter(self._keybox, self._filter_commands)
        while not self._quit:
            signal.alarm(SHELL_TIMEOUT_SECS)
            cmdline = completer.input("> ")
            signal.alarm(0)
            if not cmdline.strip():
                continue
            command, *args = cmdline.split(None, 1)
            func = None
            params = []
            if command in self._commands:
                func, params = self._command_map[command]
            else:
                filtered = self._filter_commands(command)
                if len(filtered) == 1:
                    func, params = self._command_map[filtered[0]]
            if func:
                try:
                    if len(params) > 1 and len(args):
                        args = args[0].split(None, len(params)-1)
                    func(*args)
                except KeyboardInterrupt:
                    print("^C")
                except TypeError as e:
                    print(e)
            else:
                print("Unknown command. Try 'help'.")

    def cmd_quit(self):
        """Save and quit"""
        self._quit = True

    def cmd_nowrite(self):
        """Do not write changes on quit"""
        self._write_on_quit = False

    def cmd_help(self, command=None):
        """Print list of all commands or full help for a command"""
        filtered_commands = []
        if command:
            filtered_commands = self._filter_commands(command)
            if len(filtered_commands) == 0:
                print("Not found.")
                return
            if len(filtered_commands) == 1:
                command = filtered_commands[0]
                self._print_help(command, full=True)
                return
        for command in (filtered_commands or self._commands):
            self._print_help(command)

    def _fill_commands(self):
        """Gather all commands and their signatures into `_command_map`.

        Commands are all methods beginning with prefix 'cmd_'.

        """
        self._commands = [name[4:] for name in dir(self)
                          if name.startswith('cmd_')]
        for command in self._commands:
            func = getattr(self, 'cmd_' + command)
            params = list(signature(func).parameters.values())
            self._command_map[command] = (func, params)

    def _filter_commands(self, start_text):
        return sorted(name for name in self._commands
                      if name.startswith(start_text))

    def _input(self, prompt=None):
        """Override input function to add some convenience."""
        # Special handling for cmd_add fields
        if prompt.startswith('Password:'):
            completer = PasswordCompleter()
        elif prompt.startswith('User:'):
            completer = UserCompleter(self._keybox)
        elif prompt.startswith('URL:'):
            completer = UrlCompleter()
        elif prompt.startswith('Tags:'):
            completer = TagsCompleter(self._keybox)
        else:
            completer = BaseCompleter()
        return completer.input(prompt)

    def _print_help(self, command, full=False):
        """Print help text for a `command` as found in docstring.

        Prints only one-line summary by default.
        Enable `full` to print full help text.

        """
        func, params = self._command_map[command]
        params_str = ' '.join(
            ('%s' if p.default == p.empty else '[%s]') % p.name
            for p in params)
        docstring = func.__doc__ + '\n'
        docshort, docrest = docstring.split('\n', 1)
        self._print(command.ljust(8),
                    params_str.ljust(28),
                    docshort.strip())
        if full and docrest:
            self._print('\n', textwrap.dedent(docrest).strip(), sep='')
