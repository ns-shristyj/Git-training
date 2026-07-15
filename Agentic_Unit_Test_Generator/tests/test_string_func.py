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
    """Verifies that reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies that reversing a single character returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies that reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_whitespace():
    """Verifies reversal preserves whitespace characters correctly."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_with_unicode():
    """Verifies reversal works correctly with unicode characters."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_with_special_chars_injection_payload():
    """Verifies that a script-injection-like payload is only reversed as plain text, not executed or altered semantically."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # ensure it's still just a string, not evaluated/executed
    assert isinstance(result, str)


def test_reverse_string_non_string_input_raises_type_error():
    """Verifies that passing a non-string (int) raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(123)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies basic capitalization of multiple words."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy_handled():
    """Verifies that falsy input (empty string) is handled via the explicit guard clause."""
    assert capitalize_words("") == ""


def test_capitalize_words_single_word():
    """Verifies capitalization of a single word."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_already_capitalized():
    """Verifies that already capitalized words remain properly capitalized (lowercasing rest)."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_extra_whitespace_collapsed():
    """Verifies that multiple spaces between words are collapsed by split()/join()."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace_stripped():
    """Verifies that leading/trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies capitalization behavior when words contain digits or symbols."""
    assert capitalize_words("hello-world 123abc") == "Hello-world 123abc"


def test_capitalize_words_whitespace_only_string():
    """Verifies that a string of only whitespace returns an empty string result."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_non_string_input_raises_type_error():
    """Verifies that passing a non-string type raises an AttributeError/TypeError rather than corrupting output."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------- truncate ----------

def test_truncate_text_shorter_than_max_length():
    """Verifies that text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_text_equal_to_max_length():
    """Verifies that text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_text_longer_than_max_length():
    """Verifies that text longer than max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_value_error():
    """Verifies that a zero max_length raises ValueError as per explicit validation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, preventing invalid slicing behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies that an empty string input returns an empty string with a valid positive max_length."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation boundary behavior when max_length is the smallest valid positive value."""
    assert truncate("hello", 1) == "h..."


def test_truncate_long_path_traversal_payload_truncated_safely():
    """Verifies that a path traversal-like payload is only truncated as plain text and not resolved/executed."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 5)
    assert result == "../..." 
    assert "etc/passwd" not in result


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies that passing a non-integer max_length raises a TypeError instead of unsafe comparison."""
    with pytest.raises(TypeError):
        truncate("hello world", "5")
