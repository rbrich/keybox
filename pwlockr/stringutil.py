# normalize, contains
# (string utilities)
#

import unicodedata


def normalize(text: str):
    """Prepare the `text` for string comparison.

    Replaces composed characters by basic ones and converts to lowercase.

    """
    text = unicodedata.normalize('NFKD', text)
    output = []
    for c in text:
        if not unicodedata.combining(c):
            output += [c]
    return ''.join(output).lower()


def contains(haystack: str, needle: str):
    """Check if `haystack` contains `needle`.

    Ignores case and composed characters.

    """
    return normalize(needle) in normalize(haystack)
