import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies a simple ASCII string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies reversing a single character returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies a palindrome remains unchanged after reversal."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies strings with spaces and punctuation reverse correctly."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies unicode characters are reversed without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safe():
    """Verifies a script injection-like payload is only reversed as plain text, not executed or altered."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert result != payload


def test_reverse_string_non_string_raises():
    """Verifies passing a non-string type raises a TypeError rather than silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies each word in a lowercase sentence is capitalized."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verifies falsy input (empty string) hits the early-return branch."""
    assert capitalize_words("") == ""


def test_capitalize_words_mixed_case():
    """Verifies mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies extra whitespace between words is collapsed via split()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_spaces():
    """Verifies leading/trailing whitespace is stripped by split()."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_only_whitespace():
    """Verifies a string of only whitespace returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_single_word():
    """Verifies a single word is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_numbers_and_symbols():
    """Verifies words containing digits/symbols are handled without crashing."""
    result = capitalize_words("123abc def-ghi")
    assert result == "123abc Def-ghi"


def test_capitalize_words_non_string_raises():
    """Verifies passing a non-string type raises an AttributeError rather than corrupting behavior."""
    with pytest.raises(AttributeError):
        capitalize_words(123)


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verifies text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length():
    """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_exceeds_length():
    """Verifies text longer than max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_length_raises():
    """Verifies max_length of zero raises ValueError as per the positive-length constraint."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_length_raises():
    """Verifies a negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text():
    """Verifies an empty text input with a valid max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation boundary condition with the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_path_traversal_payload_truncated_safely():
    """Verifies a path traversal-like payload is only truncated as text, not resolved as a filesystem path."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 5)
    assert result == "../.."+"..."
    assert "etc/passwd" not in result


def test_truncate_non_integer_max_length_raises():
    """Verifies a non-integer max_length raises a TypeError instead of silently misbehaving."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
