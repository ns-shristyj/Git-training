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
    def test_reverse_string_functionality(self, text, expected):
        """Verify reverse_string correctly reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    def test_reverse_string_invalid_type_raises_typeerror(self):
        """Verify reverse_string raises TypeError when given a non-sliceable type like int."""
        with pytest.raises(TypeError):
            reverse_string(123)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_capitalize_words_functionality(self, text, expected):
        """Verify capitalize_words capitalizes each word and returns empty string for empty/whitespace input."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_input_returns_empty_string(self):
        """Verify capitalize_words safely returns empty string when given None (falsy) instead of crashing."""
        assert capitalize_words(None) == ""


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("short", 10, "short"),
            ("this is a long text", 7, "this is..."),
            ("exact", 5, "exact"),
        ],
    )
    def test_truncate_functionality(self, text, max_length, expected):
        """Verify truncate returns text unchanged when within limit and appends ellipsis when exceeding it."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_invalid_max_length_raises_valueerror(self, max_length):
        """Verify truncate raises ValueError for zero or negative max_length values."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)
