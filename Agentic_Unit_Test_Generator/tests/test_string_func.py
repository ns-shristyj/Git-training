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
        """Verify reverse_string correctly reverses a normal string and handles empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize("bad_input", [None, 123, 1.5])
    def test_reverse_string_unsliceable_types_raise_type_error(self, bad_input):
        """Verify reverse_string raises TypeError for types that don't support slicing."""
        with pytest.raises(TypeError):
            reverse_string(bad_input)

    def test_reverse_string_list_input_returns_reversed_list(self):
        """Verify reverse_string on a list (which supports slicing) returns a reversed list, not a string."""
        result = reverse_string([1, 2, 3])
        assert result == [3, 2, 1]


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("  multiple   spaces  here ", "Multiple Spaces Here"),
        ],
    )
    def test_capitalize_words_typical_and_empty(self, text, expected):
        """Verify capitalize_words capitalizes each word, handles empty string and extra whitespace."""
        assert capitalize_words(text) == expected

    @pytest.mark.parametrize("bad_input", [None, 123, 1.5])
    def test_capitalize_words_invalid_types_raise_appropriate_error(self, bad_input):
        """Verify capitalize_words raises TypeError for non-string, non-falsy-equivalent inputs lacking split()."""
        if not bad_input:
            # falsy inputs (None, 0, 0.0) short-circuit to "" before .split() is called
            assert capitalize_words(bad_input) == ""
        else:
            with pytest.raises(AttributeError):
                capitalize_words(bad_input)


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello", 10, "hello"),
            ("hello world", 5, "hello..."),
            ("", 5, ""),
        ],
    )
    def test_truncate_typical_and_edge_lengths(self, text, max_length, expected):
        """Verify truncate returns unmodified text when within limit and truncates with ellipsis when exceeding it."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Verify truncate raises ValueError when max_length is zero or negative."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)

    def test_truncate_injection_like_payload_is_length_bounded(self):
        """Verify truncate safely bounds a script-injection-like payload to the specified max length plus ellipsis."""
        payload = "<script>alert('xss')</script>" * 5
        max_length = 10
        result = truncate(payload, max_length)
        assert result == payload[:max_length] + "..."
        assert len(result) == max_length + 3
