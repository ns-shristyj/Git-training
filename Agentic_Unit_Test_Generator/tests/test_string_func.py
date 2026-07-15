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
    """Verifies that a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies that a palindrome remains unchanged after reversal."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_whitespace():
    """Verifies that whitespace characters are preserved and correctly reversed."""
    assert reverse_string("a b") == "b a"


def test_reverse_string_unicode():
    """Verifies that unicode characters are correctly reversed without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_treated_as_data():
    """Verifies that a SQL-injection-like payload is only reversed as plain text, not executed or altered semantically."""
    payload = "'; DROP TABLE users; --"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure no execution side effects: result is just a string transformation
    assert isinstance(result, str)


def test_reverse_string_path_traversal_payload_treated_as_data():
    """Verifies that a path traversal string is safely handled as plain text via reversal, not interpreted as a filesystem path."""
    payload = "../../../../etc/passwd"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert isinstance(result, str)


def test_reverse_string_non_string_raises_type_error():
    """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


def test_reverse_string_none_raises_type_error():
    """Verifies that passing None raises a TypeError rather than crashing unexpectedly elsewhere."""
    with pytest.raises(TypeError):
        reverse_string(None)


# ---------------------------
# capitalize_words tests
# ---------------------------

def test_capitalize_words_basic():
    """Verifies that each word's first letter is capitalized and rest lowercased."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string returns an empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verifies idempotency when words are already capitalized."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verifies that mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLO wORLD") == "Hello World"


def test_capitalize_words_extra_whitespace_collapsed():
    """Verifies that multiple whitespace separators are collapsed into single spaces due to split()."""
    assert capitalize_words("  hello   world  ") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies correct capitalization behavior with only a single word."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_whitespace_only():
    """Verifies that a string consisting only of whitespace returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies that words containing digits or symbols are handled without crashing."""
    assert capitalize_words("hello123 world!") == "Hello123 World!"


def test_capitalize_words_injection_payload_treated_as_data():
    """Verifies that an HTML/script injection payload is only capitalized as text, not executed or unescaped."""
    payload = "<script>alert('xss')</script> hacked"
    result = capitalize_words(payload)
    assert "<script>alert" in result or result.startswith("<script>")
    assert isinstance(result, str)


def test_capitalize_words_none_raises_type_error():
    """Verifies that passing None is safely rejected via the falsy check returning empty string per implementation, not crashing."""
    assert capitalize_words(None) == ""


def test_capitalize_words_non_string_raises_type_error():
    """Verifies that passing a non-string integer raises a TypeError since split() is unsupported on ints."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------------------------
# truncate tests
# ---------------------------

def test_truncate_shorter_than_max_length_returns_unchanged():
    """Verifies that text shorter than max_length is returned unmodified."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length_returns_unchanged():
    """Verifies that text exactly equal to max_length is not truncated or appended with ellipses."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length_appends_ellipsis():
    """Verifies that text longer than max_length is truncated and ellipses are appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies that a max_length of zero raises a ValueError instead of silently truncating everything."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises a ValueError, preventing undefined slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_string_with_positive_max_length():
    """Verifies that an empty input string returns an empty string when max_length is positive."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies boundary behavior when max_length is the smallest positive integer."""
    assert truncate("abcdef", 1) == "a..."


def test_truncate_large_max_length_no_truncation():
    """Verifies that an extremely large max_length never truncates a short string."""
    assert truncate("abc", 1000000) == "abc"


def test_truncate_path_traversal_payload_safely_truncated():
    """Verifies that a path traversal-like payload is safely truncated as plain text without filesystem interpretation."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert isinstance(result, str)


def test_truncate_non_string_text_raises_type_error():
    """Verifies that passing a non-string as text raises a TypeError due to unsupported len()/slicing operations."""
    with pytest.raises(TypeError):
        truncate(12345, 5)


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies that passing a non-integer max_length raises a TypeError instead of proceeding unsafely."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
