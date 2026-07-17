import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify a simple string is reversed correctly."""
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
        """Verify reversing a string with spaces preserves all characters in reverse order."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_string(self):
        """Verify reversing a string with unicode characters works correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_chars(self):
        """Verify reversing a string containing injection-like payload does not execute anything and just reverses text."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure the payload isn't executed or altered beyond simple reversal
        assert "<script>" not in result

    def test_reverse_string_type_error_on_non_string(self):
        """Verify passing a non-string (e.g., int) raises a TypeError due to slicing being unsupported."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verify a single lowercase word gets its first letter capitalized."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verify multiple words each get capitalized correctly."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_all_uppercase_words(self):
        """Verify all-uppercase words are converted to capitalized form (first letter upper, rest lower)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verify extra whitespace between words is collapsed by split/join logic."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verify leading and trailing whitespace is stripped in the output."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verify a whitespace-only string returns an empty string since split() yields no words."""
        assert capitalize_words("   ") == ""

    def test_capitalize_words_with_numbers(self):
        """Verify words containing digits are handled without error."""
        assert capitalize_words("hello2world 123abc") == "Hello2world 123abc"

    def test_capitalize_none_raises_attribute_error(self):
        """Verify passing None raises an AttributeError instead of silently succeeding (input validation boundary)."""
        with pytest.raises(AttributeError):
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

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verify max_length of zero raises ValueError as a boundary/input validation check."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify a negative max_length raises ValueError, preventing invalid truncation logic."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_with_positive_max_length(self):
        """Verify truncating an empty string with a positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation with max_length of 1 correctly slices to one character plus ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_large_input_string(self):
        """Verify truncation handles very large input strings without error (resource exhaustion boundary check)."""
        large_text = "a" * 100000
        result = truncate(large_text, 10)
        assert result == "a" * 10 + "..."

    def test_truncate_type_error_on_non_string_text(self):
        """Verify passing a non-string text raises a TypeError since len() and slicing require string-like behavior."""
        with pytest.raises(TypeError):
            truncate(12345, 5)
