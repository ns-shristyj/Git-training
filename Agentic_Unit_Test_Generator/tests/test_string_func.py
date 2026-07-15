import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies basic reversal of a simple string."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies reversing a single character string returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies reversal preserves spaces and punctuation correctly."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies reversal handles unicode characters correctly."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safely_reversed():
    """Verifies that a script injection payload is only reversed as text, not executed or altered semantically."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure no code execution artifacts; output is just character-reversed text
    assert "<script>" not in result


def test_reverse_string_sql_injection_payload():
    """Verifies that a SQL injection style string is treated as plain text and reversed safely."""
    payload = "'; DROP TABLE users; --"
    result = reverse_string(payload)
    assert result == payload[::-1]


def test_reverse_string_non_string_raises_type_error():
    """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies basic capitalization of each word in a sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_falsy_short_circuit():
    """Verifies that a falsy value like None returns empty string due to explicit guard."""
    assert capitalize_words(None) == ""


def test_capitalize_words_already_capitalized():
    """Verifies that already-capitalized words remain the same."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verifies that mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLO wORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies that multiple whitespace separators are collapsed into single spaces via split()."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies that leading/trailing whitespace is stripped as a side-effect of split()."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies capitalization of a single word input."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_only_whitespace():
    """Verifies that a string containing only whitespace returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies that words containing numbers/symbols are capitalized without crashing."""
    assert capitalize_words("hello123 world!") == "Hello123 World!"


def test_capitalize_words_non_string_raises_type_error():
    """Verifies that a non-string, non-None input raises an AttributeError/TypeError rather than corrupting output."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verifies that text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length():
    """Verifies that text exactly equal to max_length is not truncated or appended with ellipses."""
    assert truncate("hello", 5) == "hello"


def test_truncate_basic_truncation():
    """Verifies that text longer than max_length is truncated and ellipses appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies that a zero max_length raises ValueError as a safe boundary check."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies that an empty string input with valid max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation boundary condition with the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_long_injection_payload_is_truncated_safely():
    """Verifies that a long injection-style payload is truncated and does not execute, only sliced as text."""
    payload = "<script>" + "a" * 100 + "</script>"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert len(result) == 13


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies that a non-integer max_length raises TypeError instead of silently misbehaving."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
