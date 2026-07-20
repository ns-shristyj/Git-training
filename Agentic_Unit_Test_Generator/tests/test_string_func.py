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
        ],
    )
    def test_reverse_string_functionality(self, text, expected):
        """Verifies reverse_string correctly reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [None, 42, 3.14])
    def test_reverse_string_invalid_input_raises_type_error(self, bad_input):
        """Ensures non-sliceable types (None, int, float) raise TypeError since they don't support slicing."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
        ],
    )
    def test_capitalize_words_functionality(self, text, expected):
        """Verifies capitalize_words capitalizes each word's first letter and handles an empty string."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_returns_empty_string(self):
        """Ensures a falsy non-string value like None is safely handled and returns an empty string."""
        assert capitalize_words(None) == ""

    def test_capitalize_words_invalid_type_raises_attribute_error(self):
        """Ensures a truthy non-string input (int) bypasses the falsy check and fails on .split(), raising AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(5)


class TestTruncate:
    def test_truncate_functionality(self):
        """Verifies truncate returns text unchanged when within max_length and appends '...' when exceeding it."""
        assert truncate("hello", 10) == "hello"
        assert truncate("hello world", 5) == "hello..."

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_invalid_max_length_raises_value_error(self, max_length):
        """Ensures truncate rejects non-positive max_length values by raising ValueError."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)

    def test_truncate_non_string_text_raises_type_error(self):
        """Ensures passing a non-string, non-sized text (int) fails on len() with TypeError."""
        with pytest.raises(TypeError):
            truncate(12345, 3)
