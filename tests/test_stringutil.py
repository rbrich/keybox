from keybox.stringutil import nt_escape, contains
from unicodedata import normalize


def test_contains():
    haystack = normalize('NFC', "žluťoučký kůň")
    needle = normalize('NFD', "žluťoučký")
    assert needle not in haystack
    assert contains(haystack, needle)


def test_escape():
    assert nt_escape("hello") == "hello"
    assert nt_escape("hello\n") == "hello\\n"
    assert nt_escape("a1\tb2\tc3\n") == "a1\\tb2\\tc3\\n"
    assert nt_escape("\r\0čž") == "\r\0čž"
