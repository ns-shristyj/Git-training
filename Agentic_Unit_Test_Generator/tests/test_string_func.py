import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies basic string reversal works correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies reversing a single character returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces():
    """Verifies reversal preserves spacing correctly."""
    assert reverse_string("hello world") == "dlrow olleh"


def test_reverse_string_unicode():
    """Verifies reversal handles unicode characters correctly."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safely_reversed():
    """Verifies that injection-like payloads are treated as plain text and safely reversed without execution."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert isinstance(result, str)


def test_reverse_string_path_traversal_payload():
    """Verifies that path traversal strings are treated as inert text and reversed safely."""
    payload = "../../etc/passwd"
    result = reverse_string(payload)
    assert result == payload[::-1]


def test_reverse_string_non_string_raises_typeerror():
    """Verifies that passing a non-string type raises a TypeError instead of executing unexpected behavior."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies each word's first letter is capitalized and rest lowercased."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies empty input returns empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verifies mixed case words are normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies extra whitespace between words is collapsed to single spaces."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies leading/trailing whitespace is stripped due to split()."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies single-word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_whitespace_only():
    """Verifies a whitespace-only string returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies words containing numbers/symbols are capitalized safely without crashing."""
    result = capitalize_words("hello123 world!")
    assert result == "Hello123 World!"


def test_capitalize_words_injection_payload_no_execution():
    """Verifies script-like payloads are treated as plain text and safely capitalized."""
    payload = "<script>alert('x')</script> test"
    result = capitalize_words(payload)
    assert "alert" in result.lower()
    assert isinstance(result, str)


def test_capitalize_words_none_raises_error():
    """Verifies None input is handled: since `not None` is True, function returns empty string."""
    assert capitalize_words(None) == ""


def test_capitalize_words_non_string_raises_typeerror():
    """Verifies non-string non-None input raises TypeError rather than silently succeeding."""
    with pytest.raises(TypeError):
        capitalize_words(12345)


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verifies text shorter than or equal to max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length_no_ellipsis():
    """Verifies text exactly equal to max_length is not truncated or altered."""
    assert truncate("hello", 5) == "hello"


def test_truncate_exceeds_length_appends_ellipsis():
    """Verifies text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_valueerror():
    """Verifies max_length of zero raises ValueError as required by input validation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_valueerror():
    """Verifies negative max_length raises ValueError, preventing invalid boundary behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies empty text input returns empty string without adding ellipsis."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation boundary condition works correctly with max_length of 1."""
    assert truncate("hello", 1) == "h..."


def test_truncate_injection_payload_safely_truncated():
    """Verifies injection-like payload text is truncated as plain data without special handling."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert "<script" in result  # confirms no sanitization bypass claims, just safe truncation


def test_truncate_large_max_length_no_overflow():
    """Verifies a very large max_length does not cause overflow or crash and text is unchanged."""
    text = "short"
    assert truncate(text, 10**6) == text


def test_truncate_non_string_text_raises_typeerror():
    """Verifies non-string text input raises TypeError instead of undefined behavior."""
    with pytest.raises(TypeError):
        truncate(12345, 5)


def test_truncate_non_integer_max_length_raises_typeerror():
    """Verifies non-integer max_length raises TypeError due to invalid comparison/slicing."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
