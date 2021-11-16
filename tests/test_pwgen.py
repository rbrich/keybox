from pathlib import Path
import pytest
from keybox import pwgen


def _test_wordlist():
    pwgen.load_wordlist.cache_clear()  # clear lru_cache
    words = pwgen.load_wordlist()
    for word in words:
        assert isinstance(word, str)
        assert len(word) > 0
    assert len(set(sorted(words))) == len(words), "no duplicate words"
    assert len(words) > 40_000, "enough words for password generator"


@pytest.mark.skipif(not pwgen.WORDLIST_SYSTEM_PATH.exists(),
                    reason=f"missing {str(pwgen.WORDLIST_SYSTEM_PATH)}")
def test_sys_wordlist():
    _test_wordlist()


def test_web_wordlist(monkeypatch, tmp_path):
    cache_path = tmp_path / 'words'
    monkeypatch.setattr(pwgen, 'WORDLIST_SYSTEM_PATH', Path('/does/not/exist'))
    monkeypatch.setattr(pwgen, 'WORDLIST_CACHE_PATH', cache_path)
    assert not cache_path.exists()
    _test_wordlist()  # downloaded and saved to disk
    assert cache_path.exists()
    _test_wordlist()  # loaded from disk cache


def test_generate_passphrase():
    pw = pwgen.generate_passphrase(num_upper=1, num_digits=1, num_special=1)
    assert isinstance(pw, str)
    assert len(pw) >= pwgen.MIN_LENGTH
    assert any(c.islower() for c in pw), "At least one lowercase"
    assert any(c.isupper() for c in pw), "At least one uppercase"
    assert any(c.isdigit() for c in pw), "At least one digit"
    assert any(c.isprintable() and not c.isalnum() for c in pw), \
           "At least one punctuation character."
    assert not any(c.isspace() for c in pw), "No whitespace"

    # test extension to min_length
    pw = pwgen.generate_passphrase(num_words=1, min_length=100)
    assert len(pw) >= 100


def test_generate_password():
    pw = pwgen.generate_password(length=50)
    assert len(pw) == 50
    assert all(c.isprintable() for c in pw)
