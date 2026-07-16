import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verifies basic reversal of a simple alphabetic string."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies that reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verifies that a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies that a palindrome remains unchanged after reversal."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verifies that whitespace is preserved and correctly reversed."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_unicode(self):
        """Verifies that unicode characters are handled correctly during reversal."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_characters(self):
        """Verifies that special/injection-like characters are reversed safely without execution."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure no code execution/side effect occurs - result is just a plain string
        assert isinstance(result, str)

    def test_reverse_string_non_string_raises(self):
        """Verifies that passing a non-string type raises a TypeError instead of silently failing."""
        with pytest.raises(TypeError):
            reverse_string(12345)

    def test_reverse_string_none_raises(self):
        """Verifies that passing None raises a TypeError."""
        with pytest.raises(TypeError):
            reverse_string(None)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verifies that each word in a simple sentence gets capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verifies that an empty string returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Verifies capitalization of a single lowercase word."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_already_capitalized(self):
        """Verifies that already capitalized words remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case_words(self):
        """Verifies that mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLO wORLD") == "Hello World"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verifies that extra whitespace between words is collapsed by split/join."""
        assert capitalize_words("hello   world") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verifies that a whitespace-only string returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_string_with_numbers(self):
        """Verifies that words containing numbers are handled without crashing."""
        assert capitalize_words("test123 abc456") == "Test123 Abc456"

    def test_capitalize_non_string_raises(self):
        """Verifies that a non-string input raises an AttributeError due to lack of split method."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)

    def test_capitalize_none_returns_empty(self):
        """Verifies that None is treated as falsy and returns empty string without crashing."""
        assert capitalize_words(None) == ""

    def test_capitalize_injection_payload_safe(self):
        """Verifies that script-like payloads are only capitalized as plain text, not executed."""
        payload = "<script>alert(1)</script> test"
        result = capitalize_words(payload)
        assert "<script>alert(1)</script>".capitalize() in result
        assert isinstance(result, str)


class TestTruncate:
    def test_truncate_shorter_than_max(self):
        """Verifies that text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max(self):
        """Verifies that text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max(self):
        """Verifies that text longer than max_length is truncated with ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_zero_length_raises(self):
        """Verifies that max_length of zero raises ValueError as it is not a positive integer."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_length_raises(self):
        """Verifies that a negative max_length raises ValueError."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text(self):
        """Verifies that an empty text string returns an empty string when max_length is positive."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies boundary behavior when max_length is the smallest positive integer."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_non_integer_max_length_raises(self):
        """Verifies that a non-numeric max_length raises TypeError on comparison rather than corrupting output."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_none_max_length_raises(self):
        """Verifies that None as max_length raises TypeError rather than being silently coerced."""
        with pytest.raises(TypeError):
            truncate("hello", None)

    def test_truncate_path_traversal_payload_safe(self):
        """Verifies that a path traversal-like string is treated as plain text and truncated safely."""
        payload = "../../../../etc/passwd"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert ".." not in result or result.startswith("../../..")  # no execution/resolution occurs

    def test_truncate_long_text_with_large_max_length(self):
        """Verifies correct behavior when max_length exceeds text length by a large margin."""
        text = "short"
        assert truncate(text, 1000) == text
