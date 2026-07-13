import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Reversing a simple word returns the characters in reverse order."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_palindrome():
    """Reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Reversing a sentence preserves spaces and punctuation in reversed order."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Reversing a string with unicode/multi-byte characters works correctly."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_single_char():
    """Reversing a single character string returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_injection_payload_safe():
    """Reversing a script injection payload only transforms the string without executing/interpreting it."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert "<script>" not in result  # confirms it's reversed, not left intact


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Capitalizes the first letter of each word in a simple sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Falsy input (empty string) short-circuits to empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Words already capitalized are normalized to capitalize-case (rest lowercased)."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_mixed_case():
    """Mixed case words are normalized so only first letter is uppercase."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Multiple whitespace separators between words are collapsed to single spaces via split()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Leading/trailing whitespace is stripped due to split() based tokenization."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_single_word():
    """A single word is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_numbers_and_symbols():
    """Words containing numbers or symbols are capitalized without crashing."""
    assert capitalize_words("123abc def456") == "123abc Def456"


def test_capitalize_words_whitespace_only_string():
    """A string containing only whitespace returns an empty string after split/join."""
    assert capitalize_words("   ") == ""


# ---------- truncate ----------

def test_truncate_shorter_than_max_length():
    """Text shorter than max_length is returned unchanged."""
    assert truncate("hi", 10) == "hi"


def test_truncate_equal_to_max_length():
    """Text exactly equal to max_length is returned unchanged (no ellipsis)."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length():
    """Text longer than max_length is cut and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises():
    """max_length of zero raises ValueError to prevent invalid/degenerate truncation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises():
    """Negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Empty text with a valid positive max_length returns empty string, no ellipsis."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """A max_length of exactly one truncates to a single character plus ellipsis when text is longer."""
    assert truncate("hello", 1) == "h..."


def test_truncate_does_not_execute_injection_payload():
    """Truncating a script/HTML injection payload only slices the string; it is not executed or altered beyond truncation logic."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert "alert(" not in result  # confirms payload was safely truncated before the executable part
