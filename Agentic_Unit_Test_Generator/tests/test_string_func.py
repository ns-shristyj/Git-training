"""Pytest tests for NIC_SecEng_Task.Calculator.string_func module."""
import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------------------------
# reverse_string
# ---------------------------

def test_reverse_string_basic():
    """Verify a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verify an empty string reverses to an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verify a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verify a palindrome string reverses to itself."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_spaces():
    """Verify spaces are preserved and reversed properly."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_with_unicode():
    """Verify unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_with_special_chars_injection_payload():
    """Verify injection-like payloads are treated as inert text and reversed safely."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure no execution or alteration occurred; it's just string manipulation.
    assert "script" in result


def test_reverse_string_path_traversal_payload():
    """Verify path traversal-like strings are safely reversed as plain text."""
    payload = "../../etc/passwd"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert result != payload  # confirms reversal actually happened


def test_reverse_string_non_string_input_raises():
    """Verify passing a non-string type raises a TypeError instead of silently failing."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------------------------
# capitalize_words
# ---------------------------

def test_capitalize_words_basic():
    """Verify each word in a simple sentence gets capitalized."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verify an empty string returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verify words that are already capitalized remain correctly capitalized."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_all_uppercase():
    """Verify all-uppercase words get normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verify multiple spaces between words are collapsed via split()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verify leading/trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_single_word():
    """Verify a single word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_with_numbers_and_symbols():
    """Verify words containing digits/symbols are not corrupted, only capitalization is applied."""
    assert capitalize_words("hello123 world!") == "Hello123 World!"


def test_capitalize_words_whitespace_only_returns_empty():
    """Verify a string of only whitespace results in an empty output since split() yields no words."""
    assert capitalize_words("     ") == ""


def test_capitalize_words_injection_payload_not_executed():
    """Verify script-like payload text is only capitalized, not executed or altered maliciously."""
    payload = "<script>alert('x')</script> test"
    result = capitalize_words(payload)
    assert "<script>alert('x')</script>".capitalize() in result
    assert "Test" in result


def test_capitalize_words_none_input_raises():
    """Verify passing None raises an AttributeError instead of corrupting behavior silently."""
    with pytest.raises(AttributeError):
        capitalize_words(None)


# ---------------------------
# truncate
# ---------------------------

def test_truncate_no_truncation_needed():
    """Verify text shorter than or equal to max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length_no_ellipsis():
    """Verify text exactly at max_length is returned without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_text_appends_ellipsis():
    """Verify text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_value_error():
    """Verify max_length of zero raises ValueError as it is not a positive integer."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verify negative max_length raises ValueError to prevent invalid boundary behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_string_with_positive_max_length():
    """Verify an empty text input with valid positive max_length returns empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verify truncation works correctly with the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_large_max_length_no_truncation():
    """Verify a very large max_length never truncates the text."""
    text = "short text"
    assert truncate(text, 10_000) == text


def test_truncate_injection_payload_truncated_safely():
    """Verify a script injection payload is truncated as plain text without executing."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert "<script>" not in result or result.startswith("<script>"[:8])


def test_truncate_non_integer_max_length_raises_type_error():
    """Verify passing a non-integer max_length raises TypeError due to invalid comparison/slicing."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
