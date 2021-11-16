import time
import re
from inspect import currentframe


class Expect:

    def __init__(self, expected, args=None, regex=False):
        """Match stdout against `expected`
        :param expected: Either string or callable with optional args
        :param args: Args for callable(expected)
        :param regex: Match string as regex. Default is verbatim.
        """
        self._lineno = currentframe().f_back.f_lineno
        self._expected = expected
        self._args = args
        self._regex = regex

    def __repr__(self):
        return f"line {self._lineno}: {self.__class__.__name__}({self._expected!r})"

    def __getattr__(self, item):
        raise AttributeError(f"{self!r}: unknown method '{item}'")

    def expect(self, actual):
        if callable(self._expected):
            expected = self._expected(*self._args)
        else:
            expected = self._expected
        if self._regex:
            assert re.fullmatch(expected, actual) is not None
        else:
            assert actual[:len(expected)] == expected, f"{repr(self)}, actual={actual!r}"
            return actual[len(expected):]


class ExpectCopy:

    def __init__(self, expected: str):
        """Match clipboard (copy command) against `expected`"""
        self._lineno = currentframe().f_back.f_lineno
        self._expected = expected

    def __repr__(self):
        return f"line {self._lineno}: {self.__class__.__name__}({self._expected!r})"

    def __getattr__(self, item):
        raise AttributeError(f"{self!r}: unknown method '{item}'")

    def expect_copy(self, clipboard):
        assert clipboard == self._expected, repr(self)


class Send:

    def __init__(self, text):
        self._text = text

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._text)

    def __getattr__(self, item):
        raise AttributeError(f"{self!r}: unknown method '{item}'")

    def send(self):
        return self._text


class DelayedSend:

    def __init__(self, seconds, text):
        self._seconds = seconds
        self._text = text

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._seconds)

    def __getattr__(self, item):
        raise AttributeError(f"{self!r}: unknown method '{item}'")

    def send(self):
        time.sleep(self._seconds)
        return self._text
