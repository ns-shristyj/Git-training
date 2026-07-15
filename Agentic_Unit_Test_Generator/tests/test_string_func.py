import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------------------------
# reverse_string tests
# ---------------------------

def test_reverse_string_basic():
    """Verify a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verify an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verify a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verify a palindrome reverses to itself."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces():
    """Verify spaces are preserved correctly when reversing."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_unicode():
    """Verify unicode characters are reversed without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_special_chars_injection_safe():
    """Verify injection-like payloads are only reversed, not executed or altered maliciously."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure the original malicious tag is not present verbatim (it's reversed)
    assert "<script>" not in result


def test_reverse_string_type_error_on_non_string():
    """Verify passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------------------------
# capitalize_words tests
# ---------------------------

def test_capitalize_words_basic():
    """Verify each word's first letter is capitalized in a normal sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verify an empty string returns an empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verify falsy input (empty string) is handled by the explicit guard clause."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verify words already capitalized remain properly capitalized."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_all_upper():
    """Verify all-uppercase words are normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verify multiple whitespace separators are collapsed via split()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verify leading/trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_single_word():
    """Verify a single word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_with_numbers_and_symbols():
    """Verify words containing numbers/symbols do not crash and behave as expected."""
    assert capitalize_words("hello2 world!") == "Hello2 World!"


def test_capitalize_words_whitespace_only_input():
    """Verify input containing only whitespace returns an empty string (no words)."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_type_error_on_non_string():
    """Verify passing a non-string type raises an error instead of unsafe behavior."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------------------------
# truncate tests
# ---------------------------

def test_truncate_shorter_than_max_length():
    """Verify text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length():
    """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length():
    """Verify text longer than max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises():
    """Verify max_length of zero raises a ValueError (secure boundary enforcement)."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises():
    """Verify a negative max_length raises a ValueError instead of producing invalid output."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text():
    """Verify an empty text with a positive max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verify truncation with max_length of 1 returns first character plus ellipsis when text is longer."""
    assert truncate("hello", 1) == "h..."


def test_truncate_large_input_does_not_crash():
    """Verify very large input strings are truncated safely without performance/security issues."""
    large_text = "a" * 100000
    result = truncate(large_text, 10)
    assert result == "a" * 10 + "..."


def test_truncate_type_error_on_non_integer_max_length():
    """Verify a non-integer max_length raises TypeError instead of unsafe comparison behavior."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
