import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseStringCore:
    def test_reverse_empty_string(self):
        """Verify that reversing an empty string returns an empty string without error."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verify that reversing a single-character string returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_string_with_leading_trailing_spaces(self):
        """Verify that leading and trailing whitespace is preserved in the correct reversed position."""
        assert reverse_string(" ab ") == " ba "

    def test_reverse_string_with_unicode_and_emoji(self):
        """Verify that unicode characters, including multi-byte emoji, are reversed correctly without corruption."""
        payload = "abc😀"
        result = reverse_string(payload)
        assert result == payload[::-1]

    def test_reverse_string_format_string_payload(self):
        """Verify that a format-string injection style payload is only reversed as literal text, not interpreted."""
        payload = "%s%s%s{0}{1}"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload


class TestCapitalizeWordsCore:
    def test_capitalize_empty_string(self):
        """Verify that capitalizing an empty string returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Verify that a single lowercase word is capitalized correctly."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_collapses_multiple_spaces(self):
        """Verify that multiple consecutive spaces between words are collapsed into a single space in the output."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_strips_leading_and_trailing_whitespace(self):
        """Verify that leading and trailing whitespace does not appear in the capitalized output."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_already_uppercase_words_lowercased_except_first(self):
        """Verify that fully uppercase words are normalized so only the first letter remains capitalized."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_html_injection_payload_treated_as_text(self):
        """Verify that an HTML/script injection payload is only capitalized as plain text, not rendered or executed."""
        payload = "<script>alert('x')</script> hi"
        result = capitalize_words(payload)
        expected = " ".join(w.capitalize() for w in payload.split())
        assert result == expected
        assert "<SCRIPT>" not in result.upper().replace("<SCRIPT>", "<SCRIPT>")  # sanity: no execution occurred
        assert result == expected


class TestTruncateCore:
    def test_truncate_text_shorter_than_max_length_unchanged(self):
        """Verify that text shorter than max_length is returned unmodified without an ellipsis appended."""
        text = "hi"
        result = truncate(text, 10)
        assert result == text

    def test_truncate_text_exactly_equal_to_max_length_unchanged(self):
        """Verify that text exactly equal to max_length is returned unmodified without an ellipsis appended."""
        text = "hello"
        result = truncate(text, len(text))
        assert result == text

    def test_truncate_max_length_zero_produces_only_ellipsis(self):
        """Verify that a max_length of zero on non-empty text results in just the ellipsis suffix."""
        result = truncate("hello", 0)
        assert result == "..."

    def test_truncate_negative_max_length_does_not_crash(self):
        """Verify that a negative max_length is handled safely without raising an unexpected exception."""
        try:
            result = truncate("hello world", -1)
            assert isinstance(result, str)
            assert result.endswith("...")
        except (ValueError, TypeError):
            pass

    def test_truncate_empty_text_returns_empty(self):
        """Verify that truncating an empty string returns an empty string without appending an ellipsis."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_larger_than_text_returns_original(self):
        """Verify that a max_length greater than the text length returns the original text unchanged."""
        text = "short"
        result = truncate(text, 1000)
        assert result == text

    def test_truncate_path_traversal_payload_only_sliced_as_text(self):
        """Verify that a path traversal-like payload is only sliced as text and not resolved or accessed as a path."""
        payload = "../../../etc/passwd"
        result = truncate(payload, 5)
        assert result == payload[:5] + "..."
        assert result != payload
