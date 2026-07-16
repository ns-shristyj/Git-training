import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify that a simple ASCII string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify that reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verify that a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify that a palindrome string reverses to the same value."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify that spaces are preserved in correct reversed position."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_string(self):
        """Verify that unicode characters are handled and reversed correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_characters(self):
        """Verify that special/injection-like characters are reversed but not executed or altered semantically."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure the reversed string does not equal the executable script tag form
        assert result != payload

    def test_reverse_string_with_newlines(self):
        """Verify that newline characters are preserved through reversal."""
        assert reverse_string("a\nb") == "b\na"


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify that each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify that an empty string input returns an empty string rather than raising."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_string(self):
        """Verify that a falsy-but-valid empty string still returns empty output."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify idempotency: already capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_all_uppercase_words(self):
        """Verify that uppercase words are normalized to only first letter capitalized."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verify that extra whitespace between words is collapsed by split()/join()."""
        assert capitalize_words("hello   world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verify that leading/trailing whitespace is stripped due to split() behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_single_word(self):
        """Verify that a single word input is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_string_with_numbers(self):
        """Verify that words containing digits are unaffected in a harmful way (digits stay as-is)."""
        assert capitalize_words("123abc def") == "123abc Def"

    def test_capitalize_whitespace_only_string(self):
        """Verify that a whitespace-only string returns an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_string_with_html_injection(self):
        """Verify that HTML/script-like input is capitalized as plain text, not executed or specially parsed."""
        payload = "<script>alert('x')</script> hacked"
        result = capitalize_words(payload)
        # Ensure it is treated as plain text words, not interpreted
        assert result.startswith("<script>alert('x')</script>".capitalize())
        assert "Hacked" in result


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verify that text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verify that text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verify that text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verify that a zero max_length raises ValueError to prevent invalid truncation behavior."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify that a negative max_length raises ValueError, preventing negative-index slicing issues."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_with_positive_max_length(self):
        """Verify that an empty string input with valid max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify boundary behavior when max_length is the smallest positive integer."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_large_max_length(self):
        """Verify that a very large max_length does not truncate short text."""
        assert truncate("short text", 1000000) == "short text"

    def test_truncate_with_injection_payload(self):
        """Verify that a script-injection payload longer than max_length is truncated safely as plain text."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert len(result) == 13
