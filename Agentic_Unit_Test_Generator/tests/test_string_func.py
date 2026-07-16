import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_normal_string(self):
        """Verifies a normal string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies an empty string reversed remains empty."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verifies a single character string is unchanged when reversed."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies a palindrome string reverses to itself."""
        assert reverse_string("level") == "level"

    def test_reverse_string_with_spaces(self):
        """Verifies whitespace is preserved and correctly reversed."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_unicode(self):
        """Verifies unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_chars(self):
        """Verifies special/injection-like characters are reversed but not executed or altered semantically."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure the reversed payload is not equal to the original executable payload
        assert result != payload

    def test_reverse_string_type_error_on_non_string(self):
        """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verifies a single lowercase word is capitalized."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verifies multiple words are each capitalized and joined with a single space."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verifies an empty string input returns an empty string (explicit early return)."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verifies words already capitalized remain properly capitalized (no double-caps)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verifies extra whitespace between words is collapsed due to split()/join() behavior."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verifies a whitespace-only string yields an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_words_with_numbers(self):
        """Verifies words containing numbers are handled without crashing."""
        assert capitalize_words("hello123 world456") == "Hello123 World456"

    def test_capitalize_words_with_special_characters(self):
        """Verifies special characters in words do not cause crashes or injection execution."""
        result = capitalize_words("<script>alert(1)</script> test")
        assert "test".capitalize() == "Test"
        assert result.split()[-1] == "Test"

    def test_capitalize_words_type_error_on_none(self):
        """Verifies that passing None raises an AttributeError rather than being silently accepted."""
        with pytest.raises(AttributeError):
            capitalize_words(None)


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verifies text shorter than max_length is returned unmodified."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verifies text exactly equal to max_length is returned unmodified without ellipses."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verifies text longer than max_length is truncated and ellipses are appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verifies that a max_length of zero raises ValueError (boundary condition)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verifies that a negative max_length raises ValueError, preventing malformed truncation logic."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_with_positive_max_length(self):
        """Verifies an empty string input returns an empty string when max_length is positive."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies truncation works correctly for the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_malicious_payload(self):
        """Verifies that a script injection payload is truncated safely without being executed or altered beyond expected slicing."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 8)
        assert result == payload[:8] + "..."
        assert result.startswith("<script>")

    def test_truncate_max_length_non_integer_raises_type_error(self):
        """Verifies that passing a non-integer max_length raises a TypeError due to invalid comparison/slicing."""
        with pytest.raises(TypeError):
            truncate("hello world", "5")
