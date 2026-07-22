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
            ([1, 2, 3], [3, 2, 1]),
            ((1, 2, 3), (3, 2, 1)),
        ],
    )
    def test_reverse_string_functionality(self, text, expected):
        """Verifies reverse_string correctly reverses typical/empty strings and other sliceable sequences (list, tuple)."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("invalid_input", [123, None, 3.14, {}, {"a": 1}, {1, 2, 3}])
    def test_reverse_string_invalid_input_raises_type_error(self, invalid_input):
        """Ensures non-sliceable inputs (int, None, float, dict, set) raise TypeError from the slicing operation."""
        with pytest.raises(TypeError):
            reverse_string(invalid_input)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("  multiple   spaces  here ", "Multiple Spaces Here"),
        ],
    )
    def test_capitalize_words_functionality(self, text, expected):
        """Verifies capitalize_words capitalizes each word and handles empty string correctly."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_input_returns_empty_string(self):
        """Confirms that a falsy non-string input (None) is safely handled via the 'if not text' guard."""
        assert capitalize_words(None) == ""

    def test_capitalize_words_truthy_non_string_raises_attribute_error(self):
        """Ensures a truthy non-string input bypasses the falsy guard and fails on .split() with AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(5)


class TestTruncate:
    def test_truncate_functionality(self):
        """Verifies truncate shortens long text with ellipsis and leaves short text unchanged."""
        assert truncate("hello world", 5) == "hello..."
        assert truncate("hi", 10) == "hi"

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_invalid_max_length_raises_value_error(self, max_length):
        """Ensures non-positive max_length values raise ValueError as validated by the function."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)
