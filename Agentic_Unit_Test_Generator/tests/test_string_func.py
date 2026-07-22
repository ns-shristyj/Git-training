import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello", "olleh"),
            ("", ""),
        ],
    )
    def test_reverses_string_correctly(self, text, expected):
        """Verify reverse_string reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize(
        "bad_input",
        [None, 42, 3.14, True, {}, set(), complex(1, 2)],
    )
    def test_non_sliceable_input_raises_type_error(self, bad_input):
        """Verify non-sliceable inputs across many types (None, int, float, bool, dict, set, complex) raise TypeError."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
        ],
    )
    def test_capitalizes_each_word(self, text, expected):
        """Verify capitalize_words capitalizes each word and handles an empty string."""
        assert capitalize_words(text) == expected

    def test_none_input_returns_empty_string(self):
        """Verify None input is falsy and short-circuits to return an empty string."""
        assert capitalize_words(None) == ""

    def test_non_string_truthy_input_raises_attribute_error(self):
        """Verify a truthy non-string input (int) reaches .split() and raises AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(5)


class TestTruncate:
    def test_truncate_behavior_short_and_long_text(self):
        """Verify truncate returns text unchanged when within max_length, and truncates with ellipsis when exceeding it."""
        assert truncate("hello", 10) == "hello"
        assert truncate("hello world", 5) == "hello..."

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_non_positive_max_length_raises_value_error(self, max_length):
        """Verify non-positive max_length values raise ValueError as validated by the function."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)
