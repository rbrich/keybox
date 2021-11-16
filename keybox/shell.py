# ShellUI
# (shell-like user interface)
#

import sys
import textwrap
import signal
from inspect import signature

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.completion import Completer, WordCompleter, NestedCompleter, Completion

from .ui import KeyboxUI
from .backend import timeout
from . import pwgen

SHELL_TIMEOUT_SECS = 3600  # 1 hour


class BaseInput:

    def __init__(self, placeholder=None):
        self._session = PromptSession(
            complete_while_typing=True,
            placeholder=FormattedText([('bold ansiblack', placeholder)]) if placeholder else None
        )
        self._completer = None

    def input(self, prompt):
        """Input with completion and history."""
        return self._session.prompt(FormattedText([('bold', prompt)]),
                                    completer=self._completer)

    def cancel(self, exception=TimeoutError):
        self._session.app.exit(exception=exception, style='class:exiting')


class PasswordGenCompleter(Completer):
    def __init__(self):
        self._passwords = None

    def get_completions(self, document, complete_event):
        if self._passwords is None:
            self._passwords = [pwgen.generate_passphrase() for _ in range(5)] + \
                              [pwgen.generate_password() for _ in range(5)]
        for pw in self._passwords:
            if pw.startswith(document.text_before_cursor):
                yield Completion(pw, start_position=-len(document.text_before_cursor))


class NestedOptions(dict):

    """A fake dictionary that supports partial keys.

    `get(key)` returns value also for `key` that is not contained in dict, but:
    * is a prefix of another key
    * is unique prefix, i.e. only a single key matches

    This is used to persuade NestedCompleter to allow prefix shortcuts.

    """

    def __init__(self, options):
        dict.__init__(self, {k: None for k in options})

    def get(self, key, default=None):
        candidates = tuple(k for k in self.keys() if k.startswith(key.lower()))
        if len(candidates) == 1:
            return self[candidates[0]]
        return default


class ShellInput(BaseInput):

    def __init__(self, keybox, commands):
        BaseInput.__init__(self)
        completions = NestedOptions(commands)
        completions_modify = NestedOptions(keybox.get_columns())
        completions_modify['password'] = PasswordGenCompleter()
        completions['modify'] = NestedCompleter(completions_modify)
        self._completer = NestedCompleter(completions)


class UsernameInput(BaseInput):

    def __init__(self, keybox):
        BaseInput.__init__(self, placeholder='# username / login / e-mail')
        self._completer = WordCompleter(keybox.get_column_values('user'), sentence=True)


class PasswordInput(BaseInput):

    def __init__(self):
        BaseInput.__init__(self, placeholder='# <tab> to generate')
        self._completer = PasswordGenCompleter()


class SiteInput(BaseInput):

    def __init__(self, keybox):
        BaseInput.__init__(self, placeholder='The Site')
        self._completer = WordCompleter(keybox.get_column_values('site'), sentence=True)


class UrlInput(BaseInput):

    def __init__(self, keybox):
        BaseInput.__init__(self, placeholder='https://example.com/')
        self._completer = WordCompleter(keybox.get_column_values('url'), sentence=True)


class TagsInput(BaseInput):

    def __init__(self, keybox):
        BaseInput.__init__(self, placeholder='tag1 tag2')
        self._completer = WordCompleter(keybox.get_tags())


class ShellUI(KeyboxUI):

    """Shell allows user type and execute commands.

    Uses prompt_toolkit for tab-completion and history.

    The entry point is :meth:`start`.

    """

    def __init__(self, filename=None):
        super().__init__(filename)
        self._commands = []
        self._command_map = {}  # name: (func, params)
        self._fill_commands()
        self._quit = False
        self._write_on_quit = True

        def sighup_handler(_signum, _frame):
            self.close()
        if sys.platform != "win32":
            signal.signal(signal.SIGHUP, sighup_handler)

    def start(self, readonly=False):
        """Start the shell. Returns when done."""
        if not self.open(readonly):
            return
        try:
            self.mainloop()
        except (KeyboardInterrupt, EOFError):
            # Ctrl-C, Ctrl-D
            pass
        except TimeoutError:
            print("Timeout after %s seconds." % SHELL_TIMEOUT_SECS)
        finally:
            self.close(write=self._write_on_quit)

    def mainloop(self):
        """The main loop.

        `open` must be called before this and `close` should be called after.
        See `start`.

        """
        session = ShellInput(self._keybox, self._commands)
        while not self._quit:
            with timeout(SHELL_TIMEOUT_SECS, session.cancel):
                cmdline = session.input("> ")
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
            session = PasswordInput()
        elif prompt.startswith('User:'):
            session = UsernameInput(self._keybox)
        elif prompt.startswith('Site:'):
            session = SiteInput(self._keybox)
        elif prompt.startswith('URL:'):
            session = UrlInput(self._keybox)
        elif prompt.startswith('Tags:'):
            session = TagsInput(self._keybox)
        else:
            session = BaseInput()
        return session.input(prompt)

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
        print(command.ljust(8),
              params_str.ljust(28),
              docshort.strip())
        if full and docrest:
            print('\n', textwrap.dedent(docrest).strip(), sep='')
