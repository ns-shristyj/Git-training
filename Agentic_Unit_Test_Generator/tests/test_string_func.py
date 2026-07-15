import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies that a simple string is reversed correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies that an empty string reversed remains empty."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies that a single character string is unchanged when reversed."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies that a palindrome remains the same after reversal."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies that spaces and punctuation are preserved in reversed order."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies that unicode characters are reversed correctly without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_safe():
    """Verifies that a script injection payload is only reversed as text and not executed or altered semantically."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert result != payload  # confirms it was reversed, not passed through unchanged


def test_reverse_string_non_string_raises_type_error():
    """Verifies that a non-string input raises a TypeError rather than silently succeeding."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies that each word's first letter is capitalized in a normal sentence."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies that an empty string returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verifies that falsy input like empty string short-circuits to empty output."""
    assert capitalize_words("") == ""


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies that multiple spaces between words are collapsed by split/join behavior."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies that leading and trailing whitespace is stripped from the result."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_already_uppercase():
    """Verifies that fully uppercase words are normalized to capitalized form."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verifies that mixed-case words are normalized correctly."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies correct capitalization behavior with a single word input."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies that words containing numbers or symbols are capitalized safely without crashing."""
    assert capitalize_words("123abc def!") == "123abc Def!"


def test_capitalize_words_none_raises_attribute_error():
    """Verifies that passing None raises an AttributeError instead of being silently accepted."""
    with pytest.raises(AttributeError):
        capitalize_words(None)


def test_capitalize_words_non_string_raises_error():
    """Verifies that a non-string input raises an error rather than producing invalid output."""
    with pytest.raises(AttributeError):
        capitalize_words(42)


# ---------- truncate ----------

def test_truncate_shorter_than_max_length():
    """Verifies that text shorter than max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length():
    """Verifies that text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length():
    """Verifies that text longer than max_length is truncated and appended with ellipsis."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies that a max_length of zero raises ValueError as it is not a positive integer."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies that a negative max_length raises ValueError to prevent invalid truncation boundaries."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_with_positive_max_length():
    """Verifies that empty text with a positive max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies boundary behavior when max_length is the smallest positive integer."""
    assert truncate("hello", 1) == "h..."


def test_truncate_injection_payload_is_truncated_safely():
    """Verifies that a path traversal / injection-like payload is truncated as plain text without special handling."""
    payload = "../../../etc/passwd; rm -rf /"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert "rm -rf" not in result  # confirms dangerous portion was truncated away


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies that passing a non-integer max_length raises a TypeError instead of silently succeeding."""
    with pytest.raises(TypeError):
        truncate("hello", "5")
