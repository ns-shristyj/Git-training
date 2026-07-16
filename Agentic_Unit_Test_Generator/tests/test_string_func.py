import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_word(self):
        """Verify a simple word is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verify a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify a palindrome remains unchanged after reversal."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify sentences with spaces are reversed including spaces."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_string_with_special_characters(self):
        """Verify special characters and injection-like payloads are reversed as plain data, not executed."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure no execution artifact / the payload is just data
        assert "<script>" not in result

    def test_reverse_unicode_string(self):
        """Verify unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_numeric_string(self):
        """Verify numeric strings are reversed correctly."""
        assert reverse_string("12345") == "54321"


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a simple sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify an empty string input returns an empty string, not an error."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case_words(self):
        """Verify mixed case words are normalized to first-letter-capital, rest lowercase."""
        assert capitalize_words("hELLO wORLD") == "Hello World"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verify multiple spaces between words are collapsed by split()/join()."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verify leading and trailing whitespace is stripped due to split() behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_whitespace_only_string(self):
        """Verify a whitespace-only string returns an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_with_numbers_and_symbols(self):
        """Verify words containing numbers/symbols are handled without crashing."""
        result = capitalize_words("hello123 world!")
        assert result == "Hello123 World!"

    def test_capitalize_none_input_raises(self):
        """Verify passing None raises a TypeError instead of silently corrupting data (type safety check)."""
        with pytest.raises(TypeError):
            capitalize_words(None)


class TestTruncate:
    def test_truncate_shorter_than_max_length(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length(self):
        """Verify text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises(self):
        """Verify max_length of zero raises ValueError, preventing degenerate truncation."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises(self):
        """Verify negative max_length raises ValueError, blocking invalid boundary input."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_max_length_one(self):
        """Verify truncation works correctly at the smallest valid boundary (max_length=1)."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_empty_text(self):
        """Verify truncating an empty string with a positive max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_with_path_traversal_like_payload(self):
        """Verify a path-traversal-like string is treated as plain text and safely truncated, not interpreted as a path."""
        payload = "../../../../etc/passwd"
        result = truncate(payload, 5)
        assert result == "../..."
        assert not result.startswith("/etc")

    def test_truncate_very_large_max_length(self):
        """Verify a very large max_length does not truncate short text and does not crash."""
        assert truncate("hi", 10**6) == "hi"
