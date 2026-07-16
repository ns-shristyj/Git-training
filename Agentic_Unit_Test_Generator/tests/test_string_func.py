import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseStringAdditional:
    def test_reverse_numeric_string(self):
        """Verify that a string of digits is reversed correctly without type coercion issues."""
        assert reverse_string("12345") == "54321"

    def test_reverse_string_with_tabs(self):
        """Verify that tab characters are preserved in correct reversed position."""
        assert reverse_string("a\tb") == "b\ta"

    def test_reverse_long_string_performance_safety(self):
        """Verify that a very long string is reversed without error or truncation."""
        long_str = "x" * 10000
        result = reverse_string(long_str)
        assert result == long_str  # palindrome-like since all same char
        assert len(result) == 10000

    def test_reverse_string_non_string_input_raises(self):
        """Verify that passing a non-string type raises an appropriate error rather than silently succeeding."""
        with pytest.raises((TypeError, AttributeError)):
            reverse_string(12345)

    def test_reverse_string_with_null_byte(self):
        """Verify that a null byte embedded in the string is preserved and not used to truncate the string unsafely."""
        payload = "abc\x00def"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert "\x00" in result

    def test_reverse_string_path_traversal_payload(self):
        """Verify that a path traversal-like payload is only reversed as text and not resolved as a path."""
        payload = "../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload


class TestCapitalizeWordsAdditional:
    def test_capitalize_none_input_raises(self):
        """Verify that passing None raises an error instead of silently returning invalid output."""
        with pytest.raises((TypeError, AttributeError)):
            capitalize_words(None)

    def test_capitalize_non_string_input_raises(self):
        """Verify that passing a non-string type raises an appropriate error."""
        with pytest.raises((TypeError, AttributeError)):
            capitalize_words(12345)

    def test_capitalize_string_with_tabs_and_newlines(self):
        """Verify that tabs and newlines are treated as whitespace separators and collapsed like spaces."""
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"

    def test_capitalize_words_with_hyphenated_word(self):
        """Verify that only the leading character of a hyphenated token is capitalized (no special hyphen handling)."""
        assert capitalize_words("well-known fact") == "Well-known Fact"

    def test_capitalize_words_with_sql_injection_payload(self):
        """Verify that a SQL injection-like payload is treated as plain text and merely capitalized, not executed."""
        payload = "'; drop table users; --"
        result = capitalize_words(payload)
        # capitalize() lowercases rest of the token; ensure it's plain text transformation
        assert result == " ".join(w.capitalize() for w in payload.split())
        assert "DROP TABLE" not in result


class TestTruncateAdditional:
    def test_truncate_non_string_text_raises(self):
        """Verify that passing a non-string text raises an appropriate error rather than corrupting output."""
        with pytest.raises((TypeError, AttributeError)):
            truncate(12345, 5)

    def test_truncate_non_integer_max_length_raises(self):
        """Verify that passing a non-integer max_length raises an error instead of silently misbehaving."""
        with pytest.raises((TypeError, ValueError)):
            truncate("hello world", "5")

    def test_truncate_float_max_length_behaves_or_raises(self):
        """Verify that a float max_length either slices correctly or raises a controlled error, never crashing unexpectedly."""
        try:
            result = truncate("hello world", 5.0)
            assert result == "hello..."
        except (TypeError, ValueError):
            pass

    def test_truncate_unicode_text_boundary(self):
        """Verify that truncation of unicode text respects character boundaries and appends ellipsis correctly."""
        text = "héllo wörld"
        result = truncate(text, 5)
        assert result == text[:5] + "..."

    def test_truncate_does_not_leak_beyond_original_length(self):
        """Verify that truncated output never exceeds max_length plus the length of the ellipsis suffix."""
        text = "a" * 50
        max_length = 10
        result = truncate(text, max_length)
        assert len(result) == max_length + 3

    def test_truncate_max_length_exactly_one_less_than_text(self):
        """Verify boundary condition where max_length is exactly one less than text length triggers truncation."""
        text = "hello"
        result = truncate(text, len(text) - 1)
        assert result == text[:len(text) - 1] + "..."
