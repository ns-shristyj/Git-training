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
    def test_reverses_string_typical_and_empty(self, text, expected):
        """Verifies core reversal behavior works for typical and empty strings."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize(
        "bad_input",
        [None, 12345],
    )
    def test_non_sliceable_input_raises_type_error(self, bad_input):
        """Ensures non-subscriptable inputs (None, int) raise TypeError instead of silently succeeding."""
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
    def test_capitalizes_words_typical_and_empty(self, text, expected):
        """Verifies each word is capitalized for typical input and empty string returns empty."""
        assert capitalize_words(text) == expected

    def test_none_input_returns_empty_string(self):
        """Confirms None is safely handled via the falsy check and returns empty string without error."""
        assert capitalize_words(None) == ""

    def test_non_string_non_falsy_input_raises_attribute_error(self):
        """Ensures a truthy non-string input (int) fails predictably with AttributeError on .split()."""
        with pytest.raises(AttributeError):
            capitalize_words(5)


class TestTruncate:
    def test_truncate_typical_and_no_truncation_needed(self):
        """Verifies text shorter than max_length is returned unchanged and longer text is truncated with ellipsis."""
        assert truncate("hello", 10) == "hello"
        assert truncate("hello world", 5) == "hello..."

    @pytest.mark.parametrize("max_length", [0, -5])
    def test_non_positive_max_length_raises_value_error(self, max_length):
        """Ensures zero or negative max_length is rejected with a ValueError, preventing invalid truncation bounds."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)
