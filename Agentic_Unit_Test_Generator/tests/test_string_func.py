import pytest
from NIC_SecEng_Task.Calculator.string_func import reverse_string, capitalize_words, truncate


class TestReverseString:
    @pytest.mark.parametrize("text,expected", [
        ("hello", "olleh"),
        ("", ""),
        ("a", "a"),
    ])
    def test_reverse_string_functionality(self, text, expected):
        """Verifies reverse_string correctly reverses typical and empty strings."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [123, 3.14, None])
    def test_reverse_string_invalid_type_raises_type_error(self, bad_input):
        """Ensures non-sliceable types (int, float, None) raise TypeError on slicing."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)


class TestCapitalizeWords:
    @pytest.mark.parametrize("text,expected", [
        ("hello world", "Hello World"),
        ("", ""),
        ("   ", ""),
    ])
    def test_capitalize_words_functionality(self, text, expected):
        """Verifies capitalize_words capitalizes each word and handles empty/whitespace-only strings."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_input_returns_empty_string(self):
        """Ensures None input is treated as falsy and safely returns an empty string."""
        assert capitalize_words(None) == ""

    def test_capitalize_words_non_string_truthy_raises_attribute_error(self):
        """Ensures a non-string truthy input (int) without a split() method raises AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(123)


class TestTruncate:
    @pytest.mark.parametrize("text,max_length,expected", [
        ("hello world", 5, "hello..."),
        ("short", 10, "short"),
    ])
    def test_truncate_functionality(self, text, max_length, expected):
        """Verifies truncate returns full text when within length and truncates with ellipsis when exceeding it."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Ensures a non-positive max_length raises ValueError as validated by the source code."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)

    def test_truncate_non_int_max_length_raises_type_error(self):
        """Ensures a non-numeric max_length raises TypeError on the unguarded comparison operation."""
        with pytest.raises(TypeError):
            truncate("some text", "5")
