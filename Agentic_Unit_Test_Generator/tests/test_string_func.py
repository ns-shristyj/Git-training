import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("hello", "olleh"),
            ("", ""),
            ("a", "a"),
            ([1, 2, 3], [3, 2, 1]),
            ((1, 2, 3), (3, 2, 1)),
        ],
    )
    def test_reverse_string_typical_and_empty(self, text, expected):
        """Verifies reverse_string correctly reverses sliceable sequences (str, list, tuple) and handles empty string input."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("value", [123, None, 3.14, True])
    def test_reverse_string_non_sliceable_input_raises_type_error(self, value):
        """Ensures non-sliceable input types (int, None, float, bool) raise TypeError since the function performs unguarded slicing."""
        with pytest.raises(TypeError):
            reverse_string(value)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("hello world", "Hello World"),
            ("  multiple   spaces  here ", "Multiple Spaces Here"),
        ],
    )
    def test_capitalize_words_typical_input(self, text, expected):
        """Verifies capitalize_words capitalizes the first letter of every word and normalizes whitespace via split/join."""
        assert capitalize_words(text) == expected

    @pytest.mark.parametrize("text", ["", None])
    def test_capitalize_words_falsy_input_returns_empty_string(self, text):
        """Confirms that falsy inputs (empty string or None) are safely handled and return an empty string."""
        assert capitalize_words(text) == ""

    @pytest.mark.parametrize("value", [5, 3.14, [1, 2, 3]])
    def test_capitalize_words_non_string_truthy_input_raises_attribute_error(self, value):
        """Ensures truthy non-string inputs (int, float, list) bypass the falsy check and fail on .split(), raising AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(value)


class TestTruncate:
    @pytest.mark.parametrize(
        "text,max_length,expected",
        [
            ("hello", 10, "hello"),
            ("hello world", 5, "hello..."),
            ("hello", 5, "hello"),
        ],
    )
    def test_truncate_typical_behavior(self, text, max_length, expected):
        """Verifies truncate returns text unchanged when within limit and appends ellipsis when exceeding max_length."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Ensures truncate raises ValueError for zero or negative max_length as explicitly guarded in the source."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)
