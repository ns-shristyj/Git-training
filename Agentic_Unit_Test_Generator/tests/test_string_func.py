import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    """Tests for reverse_string function."""

    def test_reverse_simple_string(self):
        """Test reversing a simple string."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Test reversing an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Test reversing a single character."""
        assert reverse_string("a") == "a"

    def test_reverse_string_with_spaces(self):
        """Test reversing a string containing spaces."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_string_with_special_characters(self):
        """Test reversing a string with special characters."""
        assert reverse_string("!@#$%") == "%$#@!"

    def test_reverse_string_with_numbers(self):
        """Test reversing a string with numbers."""
        assert reverse_string("12345") == "54321"

    def test_reverse_palindrome(self):
        """Test reversing a palindrome."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_unicode_string(self):
        """Test reversing a string with unicode characters."""
        assert reverse_string("café") == "éfac"

    def test_reverse_string_with_newlines(self):
        """Test reversing a string with newline characters."""
        assert reverse_string("hello\nworld") == "dlrow\nolleh"

    def test_reverse_string_with_tabs(self):
        """Test reversing a string with tab characters."""
        assert reverse_string("hello\tworld") == "dlrow\tolleh"


class TestCapitalizeWords:
    """Tests for capitalize_words function."""

    def test_capitalize_simple_words(self):
        """Test capitalizing simple words."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Test capitalizing an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Test capitalizing a single word."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_already_capitalized(self):
        """Test capitalizing already capitalized words."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case(self):
        """Test capitalizing mixed case words."""
        assert capitalize_words("hELLO wORLD") == "Hello World"

    def test_capitalize_with_multiple_spaces(self):
        """Test capitalizing with multiple consecutive spaces."""
        assert capitalize_words("hello  world") == "Hello World"

    def test_capitalize_with_leading_trailing_spaces(self):
        """Test capitalizing with leading and trailing spaces."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_single_character_words(self):
        """Test capitalizing single character words."""
        assert capitalize_words("a b c") == "A B C"

    def test_capitalize_with_numbers(self):
        """Test capitalizing words with numbers."""
        assert capitalize_words("hello123 world456") == "Hello123 World456"

    def test_capitalize_with_special_characters(self):
        """Test capitalizing words with special characters."""
        assert capitalize_words("hello! world?") == "Hello! World?"

    def test_capitalize_unicode_words(self):
        """Test capitalizing unicode words."""
        assert capitalize_words("café naïve") == "Café Naïve"

    def test_capitalize_only_spaces(self):
        """Test capitalizing a string with only spaces."""
        assert capitalize_words("   ") == ""


class TestTruncate:
    """Tests for truncate function."""

    def test_truncate_text_shorter_than_max_length(self):
        """Test truncating text shorter than max_length."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_text_equal_to_max_length(self):
        """Test truncating text equal to max_length."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_text_longer_than_max_length(self):
        """Test truncating text longer than max_length."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_empty_string(self):
        """Test truncating an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_single_character_max_length(self):
        """Test truncating with max_length of 1."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_max_length_zero_raises_error(self):
        """Test that max_length of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Maximum length must be a positive integer"):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_error(self):
        """Test that negative max_length raises ValueError."""
        with pytest.raises(ValueError, match="Maximum length must be a positive integer"):
            truncate("hello", -1)

    def test_truncate_large_negative_max_length_raises_error(self):
        """Test that large negative max_length raises ValueError."""
        with pytest.raises(ValueError, match="Maximum length must be a positive integer"):
            truncate("hello", -100)

    def test_truncate_with_special_characters(self):
        """Test truncating text with special characters."""
        assert truncate("!@#$%^&*()", 5) == "!@#$%..."

    def test_truncate_with_spaces(self):
        """Test truncating text with spaces."""
        assert truncate("hello world test", 8) == "hello wo..."

    def test_truncate_unicode_text(self):
        """Test truncating unicode text."""
        assert truncate("café naïve", 4) == "café..."

    def test_truncate_very_long_text(self):
        """Test truncating very long text."""
        long_text = "a" * 1000
        assert truncate(long_text, 10) == "a" * 10 + "..."

    def test_truncate_text_with_newlines(self):
        """Test truncating text with newlines."""
        assert truncate("hello\nworld\ntest", 8) == "hello\nwo..."

    def test_truncate_max_length_one_with_long_text(self):
        """Test truncating with max_length of 1 on longer text."""
        assert truncate("abcdefgh", 1) == "a..."

    def test_truncate_exact_boundary(self):
        """Test truncating at exact boundary."""
        assert truncate("12345", 3) == "123..."

    def test_truncate_large_positive_max_length(self):
        """Test truncating with very large max_length."""
        text = "hello"
        assert truncate(text, 1000000) == text
