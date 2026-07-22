import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------------------------------------------------------------------------
# reverse_string
# ---------------------------------------------------------------------------

class TestReverseString:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello", "olleh"),
            ("", ""),
        ],
    )
    def test_reverses_string_correctly(self, text, expected):
        """Verifies that reverse_string reverses typical and empty string inputs correctly."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [123, None])
    def test_non_sliceable_input_raises_type_error(self, bad_input):
        """Ensures that non-subscriptable inputs (int, None) raise TypeError instead of silently failing."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)


# ---------------------------------------------------------------------------
# capitalize_words
# ---------------------------------------------------------------------------

class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
        ],
    )
    def test_capitalizes_words_correctly(self, text, expected):
        """Verifies that capitalize_words capitalizes each word and handles empty string as a special case."""
        assert capitalize_words(text) == expected

    def test_none_input_returns_empty_string(self):
        """Ensures that a falsy non-string input (None) is safely handled and returns an empty string."""
        assert capitalize_words(None) == ""

    def test_non_string_truthy_input_raises_attribute_error(self):
        """Ensures that a truthy non-string input (int) raises AttributeError when .split() is called on it."""
        with pytest.raises(AttributeError):
            capitalize_words(5)


# ---------------------------------------------------------------------------
# truncate
# ---------------------------------------------------------------------------

class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("short", 10, "short"),
            ("this is a long string", 7, "this is..."),
        ],
    )
    def test_truncates_text_correctly(self, text, max_length, expected):
        """Verifies that truncate returns unchanged text when within limit and appends '...' when exceeding it."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -5])
    def test_non_positive_max_length_raises_value_error(self, max_length):
        """Ensures that a non-positive max_length raises ValueError as explicitly enforced by the function."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)

    def test_non_int_max_length_raises_type_error(self):
        """Ensures that a non-integer max_length (string) raises TypeError on the unguarded comparison."""
        with pytest.raises(TypeError):
            truncate("some text", "5")

    def test_large_untrusted_input_is_properly_bounded(self):
        """Ensures that very long/untrusted text input is correctly truncated to the specified safe length plus ellipsis."""
        malicious_text = "<script>alert('xss')</script>" * 1000
        result = truncate(malicious_text, 20)
        assert result == malicious_text[:20] + "..."
        assert len(result) == 23
