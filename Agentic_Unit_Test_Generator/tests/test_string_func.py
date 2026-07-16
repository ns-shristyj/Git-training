import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify basic string reversal works correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verify reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify reversal preserves spaces correctly."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_string(self):
        """Verify reversal works correctly on unicode characters."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_numeric_string(self):
        """Verify reversal works correctly on strings composed of digits."""
        assert reverse_string("12345") == "54321"

    def test_reverse_string_with_special_chars(self):
        """Verify reversal handles special/injection-like characters without executing or altering them."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert isinstance(result, str)

    def test_reverse_string_with_sql_injection_payload(self):
        """Verify reversal treats SQL-injection-like text as inert data and merely reverses it."""
        payload = "'; DROP TABLE users; --"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert "DROP TABLE" not in result  # confirms text was reversed, not left intact/executed

    def test_reverse_string_with_newlines(self):
        """Verify reversal handles strings containing newlines and tabs."""
        text = "line1\nline2\t"
        assert reverse_string(text) == text[::-1]

    def test_reverse_long_string_does_not_crash(self):
        """Verify reversal handles very long input strings without error (DoS/edge-case resilience)."""
        long_text = "x" * 100000
        result = reverse_string(long_text)
        assert result == long_text  # all same character, reversal is identical
        assert len(result) == 100000


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verify a single lowercase word gets capitalized correctly."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verify multiple words each get their first letter capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify empty string input returns empty string (explicit guard branch)."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized_words(self):
        """Verify already-capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_all_uppercase_words(self):
        """Verify all-uppercase words get lowered except the first letter."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_collapses_extra_whitespace(self):
        """Verify multiple/irregular whitespace between words is collapsed by split()."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verify a whitespace-only string (falsy check bypassed by truthy string) returns empty result."""
        assert capitalize_words("   ") == ""

    def test_capitalize_single_char_words(self):
        """Verify single-character words are capitalized correctly."""
        assert capitalize_words("a b c") == "A B C"

    def test_capitalize_words_with_numbers(self):
        """Verify words containing numbers are not corrupted by capitalization."""
        assert capitalize_words("123abc test") == "123abc Test"

    def test_capitalize_words_with_tabs_and_newlines(self):
        """Verify tabs and newlines are treated as whitespace separators and collapsed like spaces."""
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"

    def test_capitalize_words_with_special_chars(self):
        """Verify special characters embedded in words are preserved safely."""
        text = "<script> alert"
        result = capitalize_words(text)
        assert result == "<script> Alert"
        assert "<script>" in result

    def test_capitalize_words_with_path_traversal_payload(self):
        """Verify path-traversal-like text is treated as inert string data, not interpreted as a path."""
        payload = "../../etc/passwd danger"
        result = capitalize_words(payload)
        assert result == "../../etc/passwd Danger"
        assert isinstance(result, str)

    def test_capitalize_unicode_word(self):
        """Verify unicode characters are handled correctly during capitalization."""
        assert capitalize_words("héllo wörld") == "Héllo Wörld"


class TestTruncate:
    def test_truncate_text_shorter_than_max_length(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_text_equal_to_max_length(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_text_longer_than_max_length(self):
        """Verify text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verify max_length of zero raises ValueError (boundary/invalid input handling)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify negative max_length raises ValueError to prevent invalid truncation logic."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_with_valid_max_length(self):
        """Verify truncating an empty string with a positive max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation with the minimal positive max_length produces correct single-char plus ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_long_injection_payload(self):
        """Verify truncation safely handles long adversarial payloads without executing or expanding them."""
        payload = "<script>" + "A" * 1000 + "</script>"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert len(result) == 13

    def test_truncate_max_length_negative_boundary_large(self):
        """Verify a very large negative max_length still raises ValueError instead of crashing or misbehaving."""
        with pytest.raises(ValueError):
            truncate("some text", -999999)

    def test_truncate_with_unicode_text(self):
        """Verify truncation counts unicode characters correctly and appends ellipsis appropriately."""
        text = "héllo wörld"
        result = truncate(text, 5)
        assert result == text[:5] + "..."

    def test_truncate_max_length_larger_than_text_returns_original(self):
        """Verify a max_length far larger than the text length returns the text unchanged (no ellipsis added)."""
        assert truncate("hi", 1000) == "hi"

    def test_truncate_null_byte_payload_handled_safely(self):
        """Verify truncation of a null-byte injection payload does not crash and produces a plain truncated string."""
        payload = "safe\x00malicious"
        result = truncate(payload, 4)
        assert result == "safe..."
        assert isinstance(result, str)
