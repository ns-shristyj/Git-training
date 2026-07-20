import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_normal_string(self):
        """Verify a standard string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify an empty string reversed is still empty."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verify a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify a palindrome reverses to itself."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify spaces are preserved correctly during reversal."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_special_characters(self):
        """Verify special/injection-like characters are reversed safely without execution."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload  # confirm it was actually reversed, not executed/altered

    def test_reverse_unicode_string(self):
        """Verify unicode characters are reversed correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_non_string_input_raises_type_error(self):
        """Verify non-string input raises TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a simple sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify empty string returns empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_handled(self):
        """Verify falsy empty string input is handled by early return branch."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain unaffected in structure."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_uppercase_words(self):
        """Verify fully uppercase words are normalized to capitalized form."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verify multiple/extra whitespace between words is collapsed by split/join logic."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_with_numbers_and_symbols(self):
        """Verify words containing numbers/symbols are safely capitalized without crashing."""
        result = capitalize_words("123abc test-case")
        assert result == "123abc Test-case"

    def test_capitalize_non_string_input_raises_error(self):
        """Verify non-string input raises an error rather than corrupting output silently."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)


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
        """Verify max_length of zero raises ValueError (boundary security check)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify negative max_length raises ValueError instead of silently misbehaving."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text(self):
        """Verify empty text with a positive max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_very_large_max_length(self):
        """Verify a very large max_length does not truncate short text (no overflow/crash)."""
        assert truncate("short", 10**6) == "short"

    def test_truncate_max_length_one(self):
        """Verify truncation to length 1 appends ellipsis correctly for boundary case."""
        assert truncate("hello", 1) == "h..."

    @pytest.mark.parametrize("bad_max_length", [0, -1, -100])
    def test_truncate_invalid_max_length_variants_raise_value_error(self, bad_max_length):
        """Verify all non-positive max_length values are rejected with ValueError."""
        with pytest.raises(ValueError):
            truncate("some text", bad_max_length)

    def test_truncate_non_string_text_raises_error(self):
        """Verify non-string text input raises an error rather than producing corrupted output."""
        with pytest.raises(TypeError):
            truncate(12345, 3)
