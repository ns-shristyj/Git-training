import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verifies a basic string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies an empty string reverses to itself without error."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verifies a single-character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies a palindrome reverses to the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_with_whitespace(self):
        """Verifies leading/trailing whitespace is preserved and reversed properly."""
        assert reverse_string(" ab ") == " ba "

    def test_reverse_with_special_characters(self):
        """Verifies special/injection-like characters are reversed as plain text, not executed."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure the payload is not executed or altered in structure, just reversed text
        assert "<script>" not in result

    def test_reverse_unicode_string(self):
        """Verifies unicode characters are reversed correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_non_string_raises_type_error(self):
        """Verifies passing a non-string type raises a TypeError instead of silently corrupting data."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verifies a single lowercase word is capitalized correctly."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verifies multiple words are each capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verifies an empty string input returns an empty string, not an error."""
        assert capitalize_words("") == ""

    def test_capitalize_none_returns_empty(self):
        """Verifies falsy None input is handled gracefully and returns empty string."""
        assert capitalize_words(None) == ""

    def test_capitalize_already_capitalized_words(self):
        """Verifies already capitalized words remain properly capitalized (mixed case normalized)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_collapses_extra_whitespace(self):
        """Verifies multiple spaces between words are collapsed due to split()/join() behavior."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace_stripped(self):
        """Verifies leading and trailing whitespace is stripped by split()/join()."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_mixed_special_characters(self):
        """Verifies special characters within words do not break capitalization logic."""
        result = capitalize_words("hello-world foo_bar")
        assert result == "Hello-world Foo_bar"

    def test_capitalize_numeric_words(self):
        """Verifies numeric-only tokens are handled without error and left unaffected."""
        assert capitalize_words("123 abc") == "123 Abc"

    def test_capitalize_non_string_raises_type_error(self):
        """Verifies a non-string, non-empty-falsy type raises TypeError rather than corrupting output."""
        with pytest.raises(TypeError):
            capitalize_words(12345)


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verifies text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verifies max_length of zero raises ValueError as per input validation."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verifies a negative max_length raises ValueError, preventing invalid boundary usage."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_returns_empty(self):
        """Verifies an empty text input with valid max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies smallest valid positive max_length truncates correctly and appends ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_max_length_no_truncation(self):
        """Verifies an extremely large max_length does not truncate short text."""
        assert truncate("hi", 10_000_000) == "hi"

    def test_truncate_non_integer_max_length_raises_type_error(self):
        """Verifies a non-integer max_length raises TypeError instead of unpredictable comparison behavior."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_injection_like_payload_truncated_safely(self):
        """Verifies path traversal / injection-like payload text is truncated as plain data without special handling."""
        payload = "../../../etc/passwd; rm -rf /"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert result.startswith("../../../")
