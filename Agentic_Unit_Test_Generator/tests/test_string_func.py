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
        """Verifies reverse_string correctly reverses a typical string and handles empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [123, None, 3.14])
    def test_reverse_string_invalid_input_raises_type_error(self, bad_input):
        """Ensures non-subscriptable/non-sliceable types raise TypeError when reversed."""
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
    def test_capitalize_words_functionality(self, text, expected):
        """Verifies capitalize_words capitalizes each word and handles empty string."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_returns_empty_string(self):
        """Verifies that None (falsy) input safely returns an empty string due to the guard clause."""
        assert capitalize_words(None) == ""

    def test_capitalize_words_non_string_truthy_raises_attribute_error(self):
        """Ensures a truthy non-string input without .split() raises AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(123)


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello world", 5, "hello..."),
            ("hi", 10, "hi"),
        ],
    )
    def test_truncate_functionality(self, text, max_length, expected):
        """Verifies truncate shortens text and appends ellipses when exceeding max_length, and leaves short text unchanged."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Ensures truncate rejects non-positive max_length values with ValueError."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)

    def test_truncate_non_int_max_length_raises_type_error(self):
        """Ensures a non-numeric max_length raises TypeError on the comparison operation."""
        with pytest.raises(TypeError):
            truncate("some text", "5")
