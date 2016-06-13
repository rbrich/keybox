# pwgen
# (random password generator)
#

import string
from random import SystemRandom
random = SystemRandom()

MIN_LENGTH = 16
NUM_WORDS = 2
NUM_UPPER = 1
NUM_DIGITS = 1
NUM_SPECIAL = 1

WORDLIST_PATH = '/usr/share/dict/words'


def load_wordlist() -> list:
    """Load and return system word list."""
    words = getattr(load_wordlist, '_words', None)
    if words:
        return words
    with open(WORDLIST_PATH, 'r') as f:
        lines = f.readlines()
    # Drop words ending 's
    words = [ln.strip() for ln in lines if not ln.endswith("'s\n")]
    load_wordlist._words = words
    return words


def generate_password(length: int=MIN_LENGTH) -> str:
    """Generate random password containing letters, digits and symbols."""
    charlist = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(charlist) for _ in range(length))


def generate_passphrase(num_words: int=NUM_WORDS,
                        min_length: int=MIN_LENGTH,
                        num_upper: int=NUM_UPPER,
                        num_digits: int=NUM_DIGITS,
                        num_special: int=NUM_SPECIAL) -> str:
    """Generate random passphrase, based on `num_words` dictionary words.

    The passphrase is peppered by making `num_upper` letters uppercase
    and by adding `num_digits` digits and `num_special` symbol characters
    at random position.

    The generated passphrase will have at least `min_length` characters
    (random letters are added if the length of chosen words is not enough).

    Returns the passphrase.

    """
    # Choose random words and join them
    words = load_wordlist()
    charlist = list(''.join(random.choice(words) for _ in range(num_words)))
    # Add letters up to min length
    while len(charlist) + num_digits + num_special < min_length:
        charlist.append(random.choice(string.ascii_lowercase))
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
