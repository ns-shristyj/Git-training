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
    def test_reverse_string_typical_and_empty(self, text, expected):
        """Verify reverse_string correctly reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [None, 123, 1.5])
    def test_reverse_string_invalid_types_raise_type_error(self, bad_input):
        """Verify reverse_string raises TypeError when given non-subscriptable/unsliceable types."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("  multiple   spaces here ", "Multiple Spaces Here"),
            ("", ""),
        ],
    )
    def test_capitalize_words_typical_and_empty(self, text, expected):
        """Verify capitalize_words capitalizes each word and returns empty string for empty input."""
        assert capitalize_words(text) == expected


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello world", 5, "hello..."),
            ("short", 10, "short"),
        ],
    )
    def test_truncate_typical_behavior(self, text, max_length, expected):
        """Verify truncate returns full text when within limit and appends ellipsis when exceeding it."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Verify truncate raises ValueError when max_length is zero or negative."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)
