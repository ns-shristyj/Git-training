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
        """Verifies that reverse_string correctly reverses a typical string and handles an empty string."""
        assert reverse_string(text) == expected

    @pytest.mark.parametrize(
        "value",
        [None, 123, 4.5],
    )
    def test_reverse_string_invalid_input_raises_type_error(self, value):
        """Verifies that non-sliceable types raise TypeError since slicing is unguarded."""
        with pytest.raises(TypeError):
            reverse_string(value)


class TestCapitalizeWords:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("hello world", "Hello World"),
            ("", ""),
            ("  multiple   spaces  ", "Multiple Spaces"),
        ],
    )
    def test_capitalize_words_functionality(self, text, expected):
        """Verifies that capitalize_words capitalizes each word, handles empty string, and collapses extra whitespace."""
        assert capitalize_words(text) == expected

    def test_capitalize_words_invalid_input_raises_attribute_error(self):
        """Verifies that a non-string input raises AttributeError since .split() is unguarded for non-str types."""
        with pytest.raises(AttributeError):
            capitalize_words(123)

    def test_capitalize_words_security_injection_payload_not_executed(self):
        """Verifies that a script injection style payload is treated as plain text and safely capitalized without execution or alteration of structure."""
        payload = "<script>alert('xss')</script> drop table users"
        result = capitalize_words(payload)
        # Ensure it's just capitalized word-by-word text, no code execution or unexpected transformation
        assert result == "<script>Alert('xss')</script> Drop Table Users"
        assert "<script>" in result  # confirms payload preserved as inert text, not sanitized/executed


class TestTruncate:
    @pytest.mark.parametrize(
        "text, max_length, expected",
        [
            ("hello world", 5, "hello..."),
            ("hi", 10, "hi"),
        ],
    )
    def test_truncate_functionality(self, text, max_length, expected):
        """Verifies that truncate shortens text and appends ellipsis when exceeding max_length, and returns text unchanged otherwise."""
        assert truncate(text, max_length) == expected

    @pytest.mark.parametrize(
        "text, max_length",
        [
            ("hello", 0),
            ("hello", -5),
        ],
    )
    def test_truncate_invalid_max_length_raises_value_error(self, text, max_length):
        """Verifies that truncate raises ValueError when max_length is zero or negative."""
        with pytest.raises(ValueError):
            truncate(text, max_length)

    def test_truncate_security_long_payload_is_bounded(self):
        """Verifies that a very long/malicious input string is safely truncated to the specified bound, preventing unbounded output."""
        payload = "A" * 10000 + "<script>alert(1)</script>"
        result = truncate(payload, 20)
        assert len(result) == 23  # 20 chars + "..."
        assert result.endswith("...")
