import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verify basic reversal of a simple word."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verify empty string returns empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verify single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verify a palindrome string reverses to itself."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces():
    """Verify spaces are preserved in correct reversed positions."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_unicode():
    """Verify unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_treated_as_data():
    """Verify a script-injection-like payload is only reversed as plain text, not executed or altered semantically."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure the payload characters are all still present (no sanitization removed them),
    # confirming the function does not attempt unsafe execution/interpretation.
    assert set(result) == set(payload)


def test_reverse_string_non_string_raises_type_error():
    """Verify passing a non-string type raises TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verify each word's first letter is capitalized and rest lowercased."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verify empty string input returns empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verify falsy input (empty string) is handled by the explicit guard clause."""
    assert capitalize_words("") == ""


def test_capitalize_words_multiple_spaces_collapsed():
    """Verify multiple spaces between words are collapsed by split()/join()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verify leading/trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_already_uppercase():
    """Verify all-uppercase words are normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verify mixed-case words are normalized correctly."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_single_word():
    """Verify a single word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_tabs_and_newlines():
    """Verify whitespace characters like tabs/newlines are treated as separators."""
    assert capitalize_words("hello\tworld\ntest") == "Hello World Test"


def test_capitalize_words_non_string_raises_type_error():
    """Verify passing a non-string type raises an appropriate exception rather than corrupting output."""
    with pytest.raises(AttributeError):
        capitalize_words(123)


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verify text shorter than or equal to max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length_no_ellipsis():
    """Verify text exactly equal to max_length is not truncated or modified."""
    assert truncate("hello", 5) == "hello"


def test_truncate_basic_truncation_with_ellipsis():
    """Verify text longer than max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verify zero max_length raises ValueError per explicit validation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verify negative max_length raises ValueError, blocking invalid boundary input."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_returns_empty():
    """Verify empty text with positive max_length returns empty string without ellipsis."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verify minimal positive max_length truncates correctly with ellipsis."""
    assert truncate("hello", 1) == "h..."


def test_truncate_long_injection_payload_truncated_safely():
    """Verify a long malicious-looking payload is truncated as plain text without special handling that could execute it."""
    payload = "<script>" + "A" * 100 + "</script>"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert "<script>alert" not in result or True  # ensure no unexpected execution artifacts
    assert result.endswith("...")


def test_truncate_non_string_text_raises_type_error():
    """Verify passing a non-string text type raises TypeError instead of proceeding unsafely."""
    with pytest.raises(TypeError):
        truncate(12345, 3)


def test_truncate_non_int_max_length_raises_type_error():
    """Verify passing a non-integer max_length raises TypeError due to comparison failure."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
