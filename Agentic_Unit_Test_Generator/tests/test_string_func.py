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
    """Verifies an empty string reverses to an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies a single character string reverses to itself."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies a palindrome remains unchanged after reversal."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_spaces_and_punctuation():
    """Verifies strings with spaces and punctuation are reversed correctly."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode():
    """Verifies unicode characters are reversed without corruption."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_is_inert():
    """Verifies that a script injection payload is only reversed as plain text, not executed or altered."""
    payload = "<script>alert('xss')</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # ensure no evaluation/execution occurs - result is just a string
    assert isinstance(result, str)


def test_reverse_string_non_string_raises_type_error():
    """Verifies passing a non-string type raises a TypeError due to unsupported slicing."""
    with pytest.raises(TypeError):
        reverse_string(12345)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies each word in a sentence is capitalized correctly."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies an empty string returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized():
    """Verifies words that are already capitalized remain properly capitalized."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies a single word input is capitalized correctly."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_multiple_spaces_collapsed():
    """Verifies multiple spaces between words are collapsed by split()/join()."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies leading and trailing whitespace is stripped due to split() behavior."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_only_whitespace():
    """Verifies a string of only whitespace returns an empty string."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols():
    """Verifies words containing numbers or symbols are still capitalized at the first character."""
    assert capitalize_words("123abc test-case") == "123abc Test-case"


def test_capitalize_words_none_input_returns_empty():
    """Verifies that a falsy None input safely returns an empty string rather than crashing."""
    assert capitalize_words(None) == ""


def test_capitalize_words_injection_payload_capitalized_safely():
    """Verifies an injection-style payload is only text-processed, not executed."""
    payload = "<img src=x onerror=alert(1)>"
    result = capitalize_words(payload)
    assert result == "<img Src=x Onerror=alert(1)>"
    assert isinstance(result, str)


# ---------- truncate ----------

def test_truncate_shorter_than_max_length():
    """Verifies text shorter than max_length is returned unmodified."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length():
    """Verifies text exactly equal to max_length is returned unmodified without ellipses."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length():
    """Verifies text longer than max_length is truncated and ellipses are appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error():
    """Verifies a zero max_length raises a ValueError to prevent invalid truncation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error():
    """Verifies a negative max_length raises a ValueError, guarding against invalid boundary input."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text():
    """Verifies an empty text string with a valid max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation works correctly with the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_non_integer_max_length_raises_type_error():
    """Verifies passing a non-integer max_length (e.g. string) raises a TypeError on comparison."""
    with pytest.raises(TypeError):
        truncate("hello", "5")


def test_truncate_long_injection_payload_gets_safely_truncated():
    """Verifies a long injection-style payload is truncated to the requested length plus ellipses, not executed."""
    payload = "<script>" + "A" * 100 + "</script>"
    result = truncate(payload, 8)
    assert result == "<script>..."
    assert len(result) == 8 + 3


def test_truncate_path_traversal_string_truncated_as_plain_text():
    """Verifies a path traversal-like string is treated as plain text and truncated safely without filesystem access."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 10)
    assert result == "../../../..."
    assert isinstance(result, str)
