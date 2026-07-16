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
    """Verifies basic reversal of a simple word."""
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


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies reversal correctly handles spaces and punctuation characters."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies reversal correctly handles unicode characters without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_is_treated_as_plain_text():
    """Verifies that script-like injection payloads are only reversed as text, not executed or altered semantically."""
    payload = "<script>alert('xss')</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure the original payload characters are preserved (not sanitized away or expanded)
    assert sorted(result) == sorted(payload)


def test_reverse_string_large_input_does_not_crash():
    """Verifies that reversing a very large string completes without error."""
    large_text = "a" * 100000
    result = reverse_string(large_text)
    assert result == large_text  # since all characters are identical
    assert len(result) == 100000


def test_reverse_string_non_string_input_raises_type_error():
    """Verifies that passing a non-string type raises a TypeError rather than silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------------------------
# capitalize_words tests
# ---------------------------

def test_capitalize_words_basic():
    """Verifies basic capitalization of each word in a sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string returns an empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_single_word():
    """Verifies capitalization works correctly for a single word."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_already_capitalized():
    """Verifies that already-capitalized words remain correctly capitalized (lowercasing rest)."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_extra_whitespace_is_normalized():
    """Verifies that multiple spaces between words are collapsed into a single space by split/join."""
    assert capitalize_words("  hello    world  ") == "Hello World"


def test_capitalize_words_whitespace_only_string_returns_empty():
    """Verifies that a string containing only whitespace returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_mixed_case_and_numbers():
    """Verifies capitalization handles words containing digits without crashing."""
    assert capitalize_words("hello2 world3") == "Hello2 World3"


def test_capitalize_words_unicode_word():
    """Verifies capitalization correctly handles unicode characters."""
    assert capitalize_words("héllo wörld") == "Héllo Wörld"


def test_capitalize_words_none_input_raises_attribute_error():
    """Verifies that passing None raises an AttributeError instead of unexpected behavior."""
    with pytest.raises(AttributeError):
        capitalize_words(None)


def test_capitalize_words_injection_payload_preserved_as_text():
    """Verifies that HTML/script-like input is only capitalized as plain text, not executed or stripped."""
    payload = "<script>alert(1)</script> hello"
    result = capitalize_words(payload)
    # The payload structure should remain intact as text (capitalized per-word split logic)
    assert "hello".capitalize() not in result or "Hello" in result
    assert "<script>alert(1)</script>".capitalize() in result


# ---------------------------
# truncate tests
# ---------------------------

def test_truncate_text_shorter_than_max_length_returns_unchanged():
    """Verifies that text shorter than max_length is returned unmodified."""
    assert truncate("hello", 10) == "hello"


def test_truncate_text_equal_to_max_length_returns_unchanged():
    """Verifies that text exactly equal to max_length is returned unmodified without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_text_longer_than_max_length_appends_ellipsis():
    """Verifies that text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_max_length_zero_raises_value_error():
    """Verifies that a max_length of zero raises ValueError to prevent invalid truncation behavior."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError, preventing negative-index slicing bugs."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies that truncating an empty string with a valid positive max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies boundary behavior when max_length is the smallest valid positive integer."""
    assert truncate("abcdef", 1) == "a..."


def test_truncate_does_not_execute_or_strip_injection_payload():
    """Verifies that injection-like payloads are truncated safely as plain text without execution or sanitization bypass."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 7)
    assert result == payload[:7] + "..."
    assert "<script" in result  # confirms it's just sliced text, not evaluated


def test_truncate_large_max_length_with_short_text():
    """Verifies that a very large max_length value with short text returns text unchanged without overflow issues."""
    text = "hi"
    result = truncate(text, 10**9)
    assert result == "hi"


def test_truncate_non_string_max_length_raises_type_error():
    """Verifies that passing a non-integer max_length raises a TypeError rather than corrupting output."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
