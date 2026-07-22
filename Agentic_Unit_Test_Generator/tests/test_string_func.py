import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------------------------
# reverse_string
# ---------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello", "olleh"),
        ("", ""),
        ("a", "a"),
    ],
)
def test_reverse_string_functionality(text, expected):
    """Verifies reverse_string correctly reverses typical and empty strings."""
    assert reverse_string(text) == expected


@pytest.mark.parametrize("bad_input", [None, 123, 3.14])
def test_reverse_string_invalid_input_raises_type_error(bad_input):
    """Ensures reverse_string raises TypeError for non-subscriptable/unsliceable types."""
    with pytest.raises(TypeError):
        reverse_string(bad_input)


# ---------------------------
# capitalize_words
# ---------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello world", "Hello World"),
        ("", ""),
        ("  multiple   spaces  here", "Multiple Spaces Here"),
    ],
)
def test_capitalize_words_functionality(text, expected):
    """Verifies capitalize_words capitalizes each word and handles empty strings/whitespace."""
    assert capitalize_words(text) == expected


def test_capitalize_words_none_returns_empty_string():
    """Ensures capitalize_words treats None as falsy and safely returns empty string."""
    assert capitalize_words(None) == ""


def test_capitalize_words_non_string_truthy_raises_attribute_error():
    """Ensures capitalize_words raises AttributeError when given a non-string truthy value lacking split()."""
    with pytest.raises(AttributeError):
        capitalize_words(123)


# ---------------------------
# truncate
# ---------------------------

@pytest.mark.parametrize(
    "text,max_length,expected",
    [
        ("hello", 10, "hello"),
        ("hello world", 5, "hello..."),
        ("exact", 5, "exact"),
    ],
)
def test_truncate_functionality(text, max_length, expected):
    """Verifies truncate returns text unchanged if within length, and appends ellipsis if exceeded."""
    assert truncate(text, max_length) == expected


@pytest.mark.parametrize("max_length", [0, -1, -100])
def test_truncate_invalid_max_length_raises_value_error(max_length):
    """Ensures truncate raises ValueError for non-positive max_length boundary values."""
    with pytest.raises(ValueError):
        truncate("some text", max_length)


def test_truncate_non_int_max_length_raises_type_error():
    """Ensures truncate raises TypeError when max_length is a non-comparable/non-numeric type."""
    with pytest.raises(TypeError):
        truncate("some text", "not a number")
