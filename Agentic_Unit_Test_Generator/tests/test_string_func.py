import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_basic_string(self):
        """Verify a simple string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verify reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify reversing a palindrome yields the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify strings with spaces are reversed preserving all characters."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_special_characters(self):
        """Verify special characters (e.g. injection-like payloads) are reversed but not executed or altered semantically."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # ensure no code execution artifact and original chars preserved (just reordered)
        assert sorted(result) == sorted(payload)

    def test_reverse_unicode_string(self):
        """Verify unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_path_traversal_string(self):
        """Verify path traversal-like strings are simply reversed as text, not interpreted as paths."""
        payload = "../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload  # confirms it was actually reversed, not resolved


class TestCapitalizeWords:
    def test_capitalize_basic_sentence(self):
        """Verify each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify an empty string returns an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_input(self):
        """Verify falsy input (empty string) short-circuits and returns empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain properly capitalized (title case)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verify multiple whitespace separators between words are collapsed to a single space."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verify leading/trailing whitespace is stripped due to split() behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verify a whitespace-only string returns an empty string (no words to join)."""
        assert capitalize_words("   ") == ""

    def test_capitalize_mixed_case_word(self):
        """Verify mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLo wORLd") == "Hello World"

    def test_capitalize_numbers_and_symbols(self):
        """Verify words containing digits/symbols are handled without crashing."""
        assert capitalize_words("123abc !@# xyz") == "123abc !@# Xyz"

    def test_capitalize_injection_like_input(self):
        """Verify script-like injection payloads are treated as plain text words, not executed."""
        result = capitalize_words("<script>alert('x')</script> test")
        assert result.startswith("<script>alert('x')</script>".capitalize())
        assert "Test" in result


class TestTruncate:
    def test_truncate_shorter_than_max_length(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hi", 10) == "hi"

    def test_truncate_equal_to_max_length(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length(self):
        """Verify text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises(self):
        """Verify max_length of zero raises ValueError as required by validation logic."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises(self):
        """Verify negative max_length raises ValueError, blocking invalid boundary input."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_with_positive_length(self):
        """Verify an empty string with a valid positive max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation to length 1 works correctly with ellipsis appended."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_non_integer_max_length_type(self):
        """Verify passing a non-integer max_length (e.g., string) raises a TypeError instead of silently misbehaving."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_large_text_with_small_limit(self):
        """Verify large input text is safely truncated without performance or memory issues."""
        long_text = "a" * 10000
        result = truncate(long_text, 10)
        assert result == "a" * 10 + "..."
        assert len(result) == 13
