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
    def test_reverse_string_basic(self, text, expected):
        """Verifies reverse_string correctly reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    def test_reverse_string_invalid_type_raises_typeerror(self):
        """Verifies that passing a non-str (e.g. int) raises TypeError since slicing an int is unsupported."""
        with pytest.raises(TypeError):
            reverse_string(123)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("  multiple   spaces  ", "Multiple Spaces"),
        ],
    )
    def test_capitalize_words_basic(self, text, expected):
        """Verifies capitalize_words capitalizes each word, collapses whitespace, and handles empty string."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_invalid_type_raises_typeerror(self):
        """Verifies that passing a non-str (e.g. None) raises TypeError since None is falsy but not text.split()-able... actually None short-circuits to empty string via 'not text'."""
        # None is falsy, so `not text` is True, function returns "" without error.
        assert capitalize_words(None) == ""


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello", 10, "hello"),
            ("hello world", 5, "hello..."),
        ],
    )
    def test_truncate_basic(self, text, max_length, expected):
        """Verifies truncate returns unchanged text when within limit and appends ellipsis when exceeding limit."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_valueerror(self, max_length):
        """Verifies truncate raises ValueError when max_length is zero or negative."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)

    def test_truncate_untrusted_input_does_not_execute_or_expand(self):
        """Verifies that malicious-looking input (script/path traversal payload) is only sliced as plain text, not executed or expanded."""
        payload = "<script>alert('xss')</script>../../etc/passwd"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert "<script>" not in result or result.startswith(payload[:10])
