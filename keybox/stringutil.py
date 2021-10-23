# normalize, contains
# (string utilities)
#

import unicodedata


def normalize(text: str) -> str:
    """Prepare the `text` for string comparison.

    Replaces composed characters by basic ones and converts to lowercase.

    """
    text = unicodedata.normalize('NFKD', text)
    output = []
    for c in text:
        if not unicodedata.combining(c):
            output += [c]
    return ''.join(output).lower()


def contains(haystack: str, needle: str) -> bool:
    """Check if `haystack` contains `needle`.

    Ignores case and composed characters.

    """
    return normalize(needle) in normalize(haystack)


def nt_escape(text: str) -> str:
    """Newline and tab C-style escape"""
    output = ''
    tr = {
        '\\': '\\\\',
        '\n': '\\n',
        '\t': '\\t',
    }
    for c in text:
        if c in tr:
            output += tr[c]
        else:
            output += c
    return output
