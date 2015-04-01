# pwgen
# (random password generator)
#

import string
import math
from random import SystemRandom
random = SystemRandom()

WORDLIST_PATH = '/usr/share/dict/words'
NUM_WORDS = 2
NUM_SPECIAL = 2
MIN_LENGTH = 8
SEP = '_'


def load_wordlist() -> list:
    """Load and return system word list."""
    with open(WORDLIST_PATH, 'r') as f:
        words = f.readlines()
    # Drop words ending 's
    words = [w.strip() for w in words if not w.endswith("'s\n")]
    return words


def pwgen(num_words: int=NUM_WORDS, num_special: int=NUM_SPECIAL,
          min_length: int=MIN_LENGTH, sep: str=SEP, entropy: list=None) -> str:
    """Generate random password, based on `num_words` dictionary words.

    Join the words using `sep` string.
    Add at least `num_special` uppercase, digits and punctuations characters.
    Make sure resulting password length is at least `min_length` (by adding
    more special characters).

    To generate password not based on wordlist (i.e. actual password,
    not passphrase), set `num_words` to 0 and `min_length` to target length.
    All symbols will be then chosen randomly from complete alphabet.

    Returns the password.

    Entropy statistics are computed and returned in `entropy` list parameter:

    * [0] = computed entropy based on algorithm
    * [1] = rough entropy based on symbol count and number of letters

    """
    # Choose random words
    wordlist = load_wordlist() if num_words > 0 else []
    words = [random.choice(wordlist) for _ in range(num_words)]
    possibles = len(wordlist) ** num_words
    # Join the words
    letters = list(sep.join(words))
    # Add miscellaneous symbols
    symbols_to_insert = max(num_special,
                            min_length - len(letters)
                            if len(letters) < min_length else 0)
    symbols = string.ascii_letters + string.digits + string.punctuation
    possibles *= (len(letters) + 1) ** symbols_to_insert
    for _ in range(symbols_to_insert):
        ch = random.choice(symbols)
        i = random.randint(0, len(letters))
        letters.insert(i, ch)
        possibles *= len(symbols)
    # Compute entropy
    if entropy is not None:
        symbol_count = 0
        for symbols in (string.ascii_lowercase, string.ascii_uppercase,
                        string.digits, string.punctuation):
            if set(symbols).intersection(letters):
                symbol_count += len(symbols)
        entropy[:] = [math.log2(possibles),
                      math.log2(symbol_count ** len(letters))]
    return ''.join(letters)
