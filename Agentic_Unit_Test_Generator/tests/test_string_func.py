import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies a single-character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies a palindrome reversed equals itself."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies spaces and punctuation are preserved in the reversed output."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safely_reversed():
    """Verifies that a script injection-like payload is only reversed as text, not executed or altered structurally."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure the payload text is not returned unchanged (i.e., it was actually processed as data)
    assert result != payload


def test_reverse_string_path_traversal_payload_is_just_text():
    """Verifies a path traversal string is treated as plain text and reversed, not interpreted as a path."""
    payload = "../../etc/passwd"
    result = reverse_string(payload)
    assert result == "dwssap/cte/../.."
    assert isinstance(result, str)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies each word's first letter is capitalized in a simple sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verifies words that are already capitalized remain correctly capitalized."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_all_uppercase_is_lowercased_then_capitalized():
    """Verifies that capitalize() lowercases remaining letters of all-uppercase words."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies that multiple whitespace separators between words are collapsed into single spaces."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace_stripped():
    """Verifies leading and trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_only_whitespace_returns_empty():
    """Verifies a string of only whitespace returns an empty string, not spaces."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies words containing digits or symbols are handled without crashing."""
    assert capitalize_words("hello123 wor$ld") == "Hello123 Wor$ld"


def test_capitalize_words_injection_payload_not_executed():
    """Verifies an HTML/script injection payload is only text-processed, never executed or stripped unsafely."""
    payload = "<script>alert('xss')</script> hello"
    result = capitalize_words(payload)
    # Result should be a capitalized textual transformation, not an executed script
    assert "<script>alert('xss')</script>".capitalize() in result
    assert "Hello" in result


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verifies text shorter than or equal to max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length_no_ellipsis():
    """Verifies text exactly equal to max_length is not truncated or altered."""
    assert truncate("hello", 5) == "hello"


def test_truncate_applies_ellipsis_when_exceeding_length():
    """Verifies text longer than max_length is cut and ellipses are appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_value_error():
    """Verifies that a max_length of zero raises ValueError instead of returning malformed output."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_max_length_one():
    """Verifies truncation works correctly at the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_empty_string_returns_empty():
    """Verifies an empty string input with a positive max_length returns an empty string unchanged."""
    assert truncate("", 5) == ""


def test_truncate_large_payload_does_not_crash():
    """Verifies truncate safely handles a very large input string without error or resource exhaustion."""
    large_text = "a" * 100000
    result = truncate(large_text, 10)
    assert result == "a" * 10 + "..."
    assert len(result) == 13


def test_truncate_injection_payload_is_safely_cut():
    """Verifies a script injection payload exceeding max_length is truncated and marked with ellipsis, not executed."""
    payload = "<script>alert(1)</script>"
    result = truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert "</script>" not in result or result.endswith("...")
