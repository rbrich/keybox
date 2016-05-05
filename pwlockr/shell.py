# ShellUI
# (shell-like user interface)
#

import readline
import textwrap
import signal

try:
    from inspect import signature
except ImportError:
    # Python 3.2 and older (pip3 install funcsigs)
    from funcsigs import signature

from pwlockr.ui import BaseUI, DEFAULT_FILENAME
from pwlockr.pwgen import pwgen

SHELL_TIMEOUT_SECS = 60 * 60  # 1 hour


class ShellUI(BaseUI):

    """Shell allows user type and execute commands.

    Uses readline for tab-completion and history.

    The entry point is :meth:`start`.

    """

    def __init__(self, filename=DEFAULT_FILENAME):
        super().__init__(filename)
        self._commands = []
        self._command_map = {}  # name: (func, params)
        self._quit = False
        self._fill_commands()
        self._complete_candidates = []
        signal.signal(signal.SIGHUP, self._sighup_handler)
        signal.signal(signal.SIGALRM, self._sigalrm_handler)

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
            self.close()

    def mainloop(self):
        """The main loop.

        `open` must be called before this and `close` should be called after.
        See `start`.

        """
        while not self._quit:
            readline.parse_and_bind('tab: complete')
            readline.set_completer(self._complete)
            readline.set_completer_delims(' ')
            signal.alarm(SHELL_TIMEOUT_SECS)
            cmdline = input("> ")
            signal.alarm(0)
            if not cmdline:
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
        """Save locker and quit."""
        self._quit = True

    def cmd_help(self, command=None):
        """Print list of all commands or full help for a command."""
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
        return [name for name in self._commands if name.startswith(start_text)]

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
                self._complete_candidates = self._filter_commands(text)
            else:
                cmd = completed_parts[0]
                cmd = self._filter_commands(cmd)[0]
                func = getattr(self, '_complete_' + cmd, lambda p, t: [])
                self._complete_candidates = func(completed_parts, text)
        try:
            return self._complete_candidates[state]
        except IndexError:
            return None

    def _complete_modify(self, completed_parts, text):
        """Complete cmd_modify args."""
        if len(completed_parts) == 1:
            return self._locker.get_columns(text)
        else:
            return []

    def _complete_add(self, completed_parts, text):
        """Complete cmd_add args.

        Generate new random password on each <tab> press.
        Typing a number and <tab> generates password that number of words long.

        """
        if len(completed_parts) == 2:
            return [self._complete_password(text, 0)]
        return []

    def _complete_password(self, text, state):
        try:
            nwords = int(text)
        except ValueError:
            nwords = 2
        return pwgen(nwords) if state == 0 else None

    def _complete_url(self, text, state):
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

    def _complete_tags(self, text, state):
        candidates = self._locker.get_tags(text)
        try:
            return candidates[state]
        except IndexError:
            return None

    def _input(self, prompt=None):
        """Override input function to add some convenience."""
        # Special handling for cmd_add fields
        if prompt.startswith('Password:'):
            return self._input_readline(prompt, self._complete_password)
        if prompt.startswith('URL:'):
            return self._input_readline(prompt, self._complete_url, '',
                                        ['https://', 'http://'])
        if prompt.startswith('Tags:'):
            return self._input_readline(prompt, self._complete_tags, ' ')
        # No completion or history for anything else
        return self._input_readline(prompt)

    def _input_readline(self, prompt, completer=None, delims='', history=()):
        """Input with completion and history."""
        if completer is not None:
            readline.parse_and_bind('tab: complete')
            readline.set_completer(completer)
            readline.set_completer_delims(delims)
        else:
            readline.parse_and_bind('tab:')
        saved_history = self._dump_readline_history()
        self._restore_readline_history(history)
        text = super()._input(prompt)
        self._restore_readline_history(saved_history)
        return text

    def _dump_readline_history(self, clear=True) -> list:
        """Extract and clear current readline history."""
        # noinspection PyArgumentList
        history = [readline.get_history_item(i+1)
                   for i in range(readline.get_current_history_length())]
        if clear:
            readline.clear_history()
        return history

    def _restore_readline_history(self, history: list):
        """Restore readline history from a list."""
        readline.clear_history()
        for item in history:
            readline.add_history(item)

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

    def _sighup_handler(self, signum, frame):
        self.close()

    def _sigalrm_handler(self, signum, frame):
        raise TimeoutError
