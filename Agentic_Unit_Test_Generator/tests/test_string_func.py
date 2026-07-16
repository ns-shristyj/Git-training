import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------------------- reverse_string ----------------------

def test_reverse_string_basic():
    """Verify that a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verify that reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verify that a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verify that a palindrome string reverses to itself."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Verify that strings with spaces and punctuation are reversed correctly."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verify that unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_with_newlines_and_special_chars():
    """Verify that control characters like newlines are safely reversed without crashing."""
    text = "line1\nline2\t\0"
    result = reverse_string(text)
    assert result == text[::-1]
    assert len(result) == len(text)


# ---------------------- capitalize_words ----------------------

def test_capitalize_words_basic():
    """Verify that each word's first letter is capitalized and rest lowercased."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verify that an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verify that falsy string values (empty) short-circuit to empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verify that already capitalized words remain properly capitalized."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verify that multiple whitespace separators between words are collapsed to single spaces."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verify that leading/trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_single_word():
    """Verify that a single word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_only_whitespace():
    """Verify that a string of only whitespace returns an empty string (no words)."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verify that words containing numbers/symbols are handled without crashing."""
    result = capitalize_words("hello123 world!")
    assert result == "Hello123 World!"


def test_capitalize_words_injection_like_input():
    """Verify that script-like injection strings are treated as plain text and safely capitalized."""
    payload = "<script>alert(1)</script> hacked"
    result = capitalize_words(payload)
    # Ensure the function does not execute or interpret the payload, just capitalizes words
    assert result == "<script>alert(1)</script> Hacked"


# ---------------------- truncate ----------------------

def test_truncate_no_truncation_needed():
    """Verify that text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length():
    """Verify that text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_exceeds_length():
    """Verify that text longer than max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises():
    """Verify that a zero max_length raises ValueError due to invalid boundary."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises():
    """Verify that a negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_positive_max_length():
    """Verify that an empty text input with valid max_length returns empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verify truncation boundary behavior when max_length is the smallest positive value."""
    assert truncate("hello", 1) == "h..."


def test_truncate_large_max_length_no_truncation():
    """Verify that a very large max_length does not truncate short text."""
    assert truncate("short", 1000000) == "short"


def test_truncate_does_not_execute_injected_payload():
    """Verify that path traversal / injection-like text is truncated safely as plain text."""
    payload = "../../etc/passwd; rm -rf /"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert "rm -rf" not in result
