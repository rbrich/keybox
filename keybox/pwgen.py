# pwgen
# (random password generator)
#

import string
import functools
from pathlib import Path
from random import SystemRandom
random = SystemRandom()

MIN_LENGTH = 16
NUM_WORDS = 2
NUM_UPPER = 2
NUM_DIGITS = 1
NUM_SPECIAL = 0

# Prefer system wordlist, fallback to cached web download
# See: https://en.wikipedia.org/wiki/Words_(Unix)
WORDLIST_SYSTEM_PATH = Path('/usr/share/dict/words')
WORDLIST_CACHE_PATH = Path('~/.keybox/words').expanduser()
WORDLIST_WEB_URL = 'https://users.cs.duke.edu/~ola/ap/linuxwords'


def filter_wordlist(words) -> tuple:
    return tuple(w.strip() for w in words if "'" not in w)


@functools.lru_cache(maxsize=None)
def load_wordlist() -> tuple:
    """Load and return a word list."""
    # Try system dict/words
    try:
        with open(WORDLIST_SYSTEM_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Drop words containing "'"
        return filter_wordlist(lines)
    except FileNotFoundError:
        pass
    # Try cached downloaded words
    try:
        with open(WORDLIST_CACHE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return filter_wordlist(lines)
    except FileNotFoundError:
        pass
    # Try web download
    import urllib.request
    with urllib.request.urlopen(WORDLIST_WEB_URL) as f:
        content = f.read()
    WORDLIST_CACHE_PATH.parent.mkdir(0o700, exist_ok=True)
    with open(WORDLIST_CACHE_PATH, 'wb') as f:
        f.write(content)
    words = content.decode('utf-8').splitlines()
    return filter_wordlist(words)


def generate_password(length: int = MIN_LENGTH) -> str:
    """Generate random password containing letters, digits and symbols."""
    charlist = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(charlist) for _ in range(length))


def generate_passphrase(num_words: int = NUM_WORDS,
                        min_length: int = MIN_LENGTH,
                        num_upper: int = NUM_UPPER,
                        num_digits: int = NUM_DIGITS,
                        num_special: int = NUM_SPECIAL) -> str:
    """Generate random passphrase, based on dictionary words.

    The passphrase is peppered by making some letters uppercase,
    by adding some digits and special symbol characters at random positions.

    :param num_words:  Use at least this many random words as basis
    :param min_length: Add more words to achieve at least this length
    :param num_upper:  Convert this many letters to uppercase
    :param num_digits: Add this many digits
    :param num_special: Add this many special symbols
    :returns: The passphrase.

    """
    # Choose random words and join them
    words = load_wordlist()
    charlist = list(''.join(random.choice(words) for _ in range(num_words)))
    # Add more words up to min length
    while len(charlist) + num_digits + num_special < min_length:
        charlist += list(random.choice(words))
    # Make some chars uppercase
    assert(num_upper <= min_length)
    indices = set()
    while len(indices) < num_upper:
        i = random.randrange(0, len(charlist))
        indices.add(i)
        charlist[i] = charlist[i].upper()
    # Add digits
    for _ in range(num_digits):
        ch = random.choice(string.digits)
        i = random.randint(0, len(charlist))
        charlist.insert(i, ch)
    # Add special chars
    for _ in range(num_special):
        ch = random.choice(string.punctuation)
        i = random.randint(0, len(charlist))
        charlist.insert(i, ch)
    return ''.join(charlist)


if __name__ == '__main__':
    for _ in range(10):
        print(generate_password(), ' ', generate_passphrase())
