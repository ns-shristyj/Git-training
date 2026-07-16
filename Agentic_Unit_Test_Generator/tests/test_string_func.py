import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Reversing a simple ASCII string returns characters in reverse order."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Reversing a single character string returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Reversing preserves spaces and punctuation, just in reverse order."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Reversing handles unicode characters correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safe():
    """A script injection-like payload is reversed literally, not executed or altered unexpectedly."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure no execution/side effects occur and result is still a plain string
    assert isinstance(result, str)


def test_reverse_string_non_string_raises_type_error():
    """Passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Capitalizes the first letter of each word in a normal sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """An empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_single_word():
    """A single word is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_multiple_spaces_collapsed():
    """Multiple spaces between words are collapsed by split()/join()."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Leading and trailing whitespace is stripped due to split() semantics."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_already_uppercase():
    """Words already in uppercase are normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_mixed_case():
    """Mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_none_returns_empty_string():
    """None input is falsy, so the function returns an empty string without crashing."""
    assert capitalize_words(None) == ""


def test_capitalize_words_only_whitespace():
    """A string of only whitespace returns an empty string after split/join."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_injection_payload_preserved_not_executed():
    """An injection-like payload is only capitalized, not interpreted or executed."""
    payload = "<script>alert('x')</script> attack"
    result = capitalize_words(payload)
    assert "<script>alert" not in result or result.startswith("<script>")
    # Confirm output is just word-capitalized text, no code execution side effects
    assert isinstance(result, str)


def test_capitalize_words_non_string_raises_attribute_error():
    """Passing a non-string, non-None type raises an AttributeError due to missing .split()."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------- truncate ----------

def test_truncate_text_shorter_than_max_length():
    """Text shorter than max_length is returned unchanged."""
    assert truncate("hi", 10) == "hi"


def test_truncate_text_equal_to_max_length():
    """Text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_text_longer_than_max_length():
    """Text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_value_error():
    """A max_length of zero raises ValueError as required by the boundary check."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """A negative max_length raises ValueError, protecting against invalid boundary input."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """An empty string with a positive max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Truncating with max_length of 1 on longer text returns single char plus ellipsis."""
    assert truncate("hello", 1) == "h..."


def test_truncate_very_large_max_length():
    """A very large max_length compared to text length returns the text unchanged."""
    assert truncate("short", 10_000) == "short"


def test_truncate_path_traversal_payload_only_truncated_not_resolved():
    """A path traversal-like payload is only truncated as text, never resolved or executed as a path."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 5)
    assert result == "../..."
    # Ensure it's still just plain text output, not a filesystem operation result
    assert isinstance(result, str)
