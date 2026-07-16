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
    """Verifies reversal of a single character string returns itself unchanged."""
    assert reverse_string("z") == "z"


def test_reverse_string_palindrome():
    """Verifies that a palindrome remains unchanged after reversal."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_internal_whitespace():
    """Verifies reversal correctly preserves and reorders internal whitespace."""
    assert reverse_string("one two") == "owt eno"


def test_reverse_string_unicode_accents():
    """Verifies reversal correctly handles accented unicode characters without corruption."""
    assert reverse_string("café") == "éfac"


def test_reverse_string_emoji_not_corrupted():
    """Verifies reversal safely handles multi-byte emoji characters without raising or mangling encoding."""
    result = reverse_string("ab😀cd")
    assert result == "dc😀ba"


def test_reverse_string_script_injection_payload_treated_as_data():
    """Verifies a script-injection-like payload is reversed as plain text, not executed or altered semantically."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert "<script>" not in result


def test_reverse_string_sql_injection_payload_treated_as_data():
    """Verifies an SQL-injection-like payload is safely reversed as inert text data."""
    payload = "'; DROP TABLE users; --"
    result = reverse_string(payload)
    assert result == payload[::-1]


def test_reverse_string_path_traversal_payload():
    """Verifies path traversal strings are treated as plain data and reversed literally."""
    payload = "../../etc/passwd"
    assert reverse_string(payload) == payload[::-1]


def test_reverse_string_non_string_int_raises_typeerror():
    """Verifies that passing an integer raises TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


def test_reverse_string_non_string_none_raises_typeerror():
    """Verifies that passing None raises TypeError instead of returning a corrupted result."""
    with pytest.raises(TypeError):
        reverse_string(None)


def test_reverse_string_non_string_list_raises_typeerror():
    """Verifies that passing a list raises TypeError rather than reversing the list silently."""
    with pytest.raises(TypeError):
        reverse_string(["a", "b", "c"])


# ---------------------------
# capitalize_words tests
# ---------------------------

def test_capitalize_words_basic():
    """Verifies basic capitalization of each word in a two-word sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string_returns_empty():
    """Verifies that an empty string input short-circuits and returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_single_word():
    """Verifies capitalization works correctly for a single lowercase word."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_multiple_internal_spaces_collapsed():
    """Verifies that multiple consecutive spaces between words are collapsed via split/join."""
    assert capitalize_words("foo    bar") == "Foo Bar"


def test_capitalize_words_mixed_case_normalized():
    """Verifies that mixed-case words are normalized to a single capitalized form per word."""
    assert capitalize_words("hELLO wORLD") == "Hello World"


def test_capitalize_words_strips_leading_trailing_whitespace():
    """Verifies leading and trailing whitespace is stripped due to split() semantics."""
    assert capitalize_words("   hi there   ") == "Hi There"


def test_capitalize_words_whitespace_only_string_returns_empty():
    """Verifies a string containing only whitespace collapses to an empty result."""
    assert capitalize_words("     ") == ""


def test_capitalize_words_with_numbers_and_symbols_preserved():
    """Verifies capitalization handles words containing digits/symbols without altering them beyond casing."""
    assert capitalize_words("abc123 def!") == "Abc123 Def!"


def test_capitalize_words_already_capitalized_unchanged():
    """Verifies that an already correctly capitalized sentence remains unchanged."""
    assert capitalize_words("Hello World") == "Hello World"


def test_capitalize_words_injection_like_payload_not_executed():
    """Verifies an HTML-injection-like payload is only capitalized as text, never interpreted."""
    payload = "<img src=x onerror=alert(1)>"
    result = capitalize_words(payload)
    assert "<script>" not in result
    assert isinstance(result, str)


def test_capitalize_words_non_string_int_raises_attributeerror():
    """Verifies that passing an integer raises AttributeError rather than corrupting output silently."""
    with pytest.raises(AttributeError):
        capitalize_words(123)


def test_capitalize_words_non_string_none_raises_attributeerror():
    """Verifies that passing None raises AttributeError instead of returning a bogus string."""
    with pytest.raises(AttributeError):
        capitalize_words(None)


# ---------------------------
# truncate tests
# ---------------------------

def test_truncate_shorter_than_max_length_unchanged():
    """Verifies text shorter than max_length is returned unchanged without ellipsis."""
    assert truncate("hi", 10) == "hi"


def test_truncate_equal_to_max_length_unchanged():
    """Verifies text exactly equal to max_length is returned unchanged without ellipsis appended."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length_appends_ellipsis():
    """Verifies text longer than max_length is truncated to max_length chars plus ellipsis."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_one_char_over_boundary():
    """Verifies truncation behavior precisely at max_length + 1 characters."""
    assert truncate("hellox", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies that a zero max_length raises ValueError to prevent degenerate truncation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, blocking malicious/invalid input."""
    with pytest.raises(ValueError):
        truncate("hello", -1)


def test_truncate_empty_string_with_positive_max_length_returns_empty():
    """Verifies that an empty string input returns an empty string when max_length is positive."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one_boundary():
    """Verifies truncation boundary condition when max_length is exactly 1."""
    assert truncate("hello", 1) == "h..."


def test_truncate_non_integer_string_max_length_raises_type_error():
    """Verifies that a string max_length raises TypeError instead of producing incorrect slicing."""
    with pytest.raises(TypeError):
        truncate("hello", "5")


def test_truncate_non_integer_float_max_length_raises_type_error():
    """Verifies that a float max_length raises TypeError to enforce strict type validation."""
    with pytest.raises(TypeError):
        truncate("hello", 5.5)


def test_truncate_none_text_raises_type_error():
    """Verifies that passing None as text raises TypeError rather than crashing unpredictably."""
    with pytest.raises(TypeError):
        truncate(None, 5)


def test_truncate_large_input_does_not_crash_or_leak_memory_excessively():
    """Verifies truncation safely handles very large input strings without performance or security issues."""
    long_text = "b" * 1_000_000
    result = truncate(long_text, 10)
    assert result == "b" * 10 + "..."


def test_truncate_injection_payload_safely_truncated():
    """Verifies a script-injection-like payload is truncated as plain text without being executed or expanded."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert "<script>alert('xss')</script>" not in result or len(result) < len(payload)
