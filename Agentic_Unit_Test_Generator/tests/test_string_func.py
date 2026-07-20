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
            ("a", "a"),
            ("racecar", "racecar"),
        ],
    )
    def test_reverse_string_basic(self, text, expected):
        """Verifies reverse_string correctly reverses a typical string, single char, palindrome, and empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize(
        "value",
        [123, 1.5, [1, 2, 3], {"a": 1}, None, True],
    )
    def test_reverse_string_non_string_input_raises_typeerror(self, value):
        """Verifies that passing non-string types (int, float, list, dict, None, bool) raises TypeError since slicing is unsupported or produces wrong semantics."""
        with pytest.raises(TypeError):
            reverse_string(value)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("  multiple   spaces  ", "Multiple Spaces"),
            ("single", "Single"),
        ],
    )
    def test_capitalize_words_basic(self, text, expected):
        """Verifies capitalize_words capitalizes each word, collapses whitespace, and handles empty string."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_none_returns_empty_string(self):
        """Verifies that passing None short-circuits via the falsy check and returns an empty string without error."""
        assert capitalize_words(None) == ""

    @pytest.mark.parametrize(
        "value",
        [123, 1.5, [1, 2, 3], {"a": 1}, True],
    )
    def test_capitalize_words_non_string_truthy_input_raises_attributeerror(self, value):
        """Verifies that non-string truthy types (int, float, list, dict, bool) bypass the falsy check and raise AttributeError since they lack a split() method."""
        with pytest.raises(AttributeError):
            capitalize_words(value)


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello", 10, "hello"),
            ("hello world", 5, "hello..."),
            ("exact", 5, "exact"),
        ],
    )
    def test_truncate_basic(self, text, max_length, expected):
        """Verifies truncate returns unchanged text when within limit, appends ellipsis when exceeding limit, and leaves exact-length text unchanged."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_valueerror(self, max_length):
        """Verifies truncate raises ValueError when max_length is zero or negative."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)

    @pytest.mark.parametrize(
        "value",
        [123, 1.5, [1, 2, 3], {"a": 1}, None],
    )
    def test_truncate_non_string_input_raises_typeerror(self, value):
        """Verifies that passing non-string types (int, float, list, dict, None) raises TypeError since len()/slicing semantics fail for these types."""
        with pytest.raises(TypeError):
            truncate(value, 5)

    def test_truncate_untrusted_input_is_sliced_as_plain_text_only(self):
        """Verifies that malicious-looking input (script/path traversal payload) is only sliced as plain text and not executed, expanded, or sanitized specially."""
        payload = "<script>alert('xss')</script>../../etc/passwd"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
