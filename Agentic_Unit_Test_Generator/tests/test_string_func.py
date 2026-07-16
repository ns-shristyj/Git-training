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
    """Verifies basic reversal of a simple ASCII string."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies that reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies reversal of a single character string returns itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies that a palindrome remains unchanged after reversal."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces():
    """Verifies reversal correctly handles internal whitespace."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_unicode():
    """Verifies reversal correctly handles unicode characters without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_special_chars_injection_like():
    """Verifies reversal safely handles input resembling injection payloads without executing anything."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure the original payload substring is not reproduced verbatim in a dangerous way
    assert "<script>" not in result


def test_reverse_string_path_traversal_like():
    """Verifies reversal safely treats path traversal strings as plain data."""
    payload = "../../etc/passwd"
    result = reverse_string(payload)
    assert result == "dwossap/cte/../.."


def test_reverse_string_non_string_raises_typeerror():
    """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------------------------
# capitalize_words tests
# ---------------------------

def test_capitalize_words_basic():
    """Verifies basic capitalization of each word in a sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verifies that falsy input (empty string) short-circuits and returns empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_single_word():
    """Verifies capitalization works correctly for a single word."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies that multiple spaces between words are collapsed by split/join."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_mixed_case_input():
    """Verifies that mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLO wORLD") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies leading and trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies capitalization handles words containing numbers or symbols without crashing."""
    assert capitalize_words("hello2 world!") == "Hello2 World!"


def test_capitalize_words_non_string_raises_attributeerror():
    """Verifies that passing a non-string type raises an AttributeError rather than corrupting output."""
    with pytest.raises(AttributeError):
        capitalize_words(123)


# ---------------------------
# truncate tests
# ---------------------------

def test_truncate_shorter_than_max_length():
    """Verifies text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length():
    """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length():
    """Verifies text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies that a zero max_length raises ValueError to prevent invalid truncation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, preventing malicious/invalid input."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_string_with_positive_max_length():
    """Verifies that an empty string input returns an empty string when max_length is positive."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation boundary condition when max_length is exactly 1."""
    assert truncate("hello", 1) == "h..."


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies that a non-integer max_length raises TypeError instead of producing incorrect output."""
    with pytest.raises(TypeError):
        truncate("hello", "5")


def test_truncate_large_input_does_not_crash():
    """Verifies truncation safely handles very large input strings without performance/security issues."""
    long_text = "a" * 1_000_000
    result = truncate(long_text, 10)
    assert result == "a" * 10 + "..."
