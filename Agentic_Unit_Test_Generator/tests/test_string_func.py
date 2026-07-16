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
    """Verifies a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies a palindrome remains unchanged when reversed."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies spaces and punctuation are preserved and reversed in place."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safely_reversed():
    """Verifies a script injection payload is treated as plain text and merely reversed, not executed or altered."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # ensure no execution/interpretation occurred - it's just a plain reversed string
    assert "<script>" not in result


def test_reverse_string_non_string_raises_type_error():
    """Verifies passing a non-string type raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------------------------
# capitalize_words
# ---------------------------

def test_capitalize_words_basic():
    """Verifies each word's first letter is capitalized in a normal sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies an empty string returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy_handled():
    """Verifies falsy input (empty string) is handled by the explicit guard clause."""
    assert capitalize_words("") == ""


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies multiple whitespace separators between words are collapsed to single spaces."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_already_uppercase():
    """Verifies fully uppercase words are normalized to capitalized form (first letter upper, rest lower)."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verifies mixed-case words are normalized correctly per Python's str.capitalize behavior."""
    assert capitalize_words("hELLo wORLd") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace_stripped():
    """Verifies leading and trailing whitespace is stripped due to str.split() behavior."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies a single word is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_numbers_and_symbols():
    """Verifies words containing numbers/symbols are processed without crashing."""
    assert capitalize_words("123abc test") == "123abc Test"


def test_capitalize_words_whitespace_only_returns_empty():
    """Verifies a string consisting only of whitespace results in an empty output (no words)."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_non_string_raises_error():
    """Verifies passing a non-string, non-empty-falsy type raises an AttributeError instead of corrupting output."""
    with pytest.raises(AttributeError):
        capitalize_words(12345)


# ---------------------------
# truncate
# ---------------------------

def test_truncate_text_shorter_than_max_length():
    """Verifies text shorter than max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 10) == "hello"


def test_truncate_text_equal_to_max_length():
    """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_text_longer_than_max_length():
    """Verifies text longer than max_length is truncated and ellipsis is appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies max_length of zero raises ValueError as required by input validation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies a negative max_length raises ValueError, preventing invalid boundary handling."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies an empty string input with a valid positive max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation works correctly at the smallest valid positive max_length boundary."""
    assert truncate("hello", 1) == "h..."


def test_truncate_long_injection_payload_is_truncated_safely():
    """Verifies a long malicious payload is truncated to the specified length and does not bypass truncation logic."""
    payload = "<script>" + "A" * 1000 + "</script>"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert len(result) == 13


def test_truncate_non_string_text_raises_type_error():
    """Verifies passing a non-string text raises TypeError instead of producing unexpected behavior."""
    with pytest.raises(TypeError):
        truncate(12345, 5)


def test_truncate_non_int_max_length_raises_type_error():
    """Verifies passing a non-integer max_length raises TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
