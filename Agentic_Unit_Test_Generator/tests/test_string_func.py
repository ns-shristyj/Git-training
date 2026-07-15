import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify a simple ASCII string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verify a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify a palindrome string reverses to itself."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify spaces are preserved and reversed along with characters."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_string(self):
        """Verify unicode characters are correctly reversed."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_chars(self):
        """Verify special/injection-like characters are reversed but not executed or altered semantically."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure no execution side-effect / the string is just data
        assert "<script>" not in result

    def test_reverse_non_string_raises(self):
        """Verify passing a non-subscriptable-reversible type raises an appropriate error."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_already_capitalized(self):
        """Verify already-capitalized words remain properly capitalized (rest lowercased)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_collapses_extra_whitespace(self):
        """Verify multiple whitespace between words is collapsed to single spaces via split/join."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verify a string containing only whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_with_numbers_and_symbols(self):
        """Verify words containing numbers/symbols are capitalized without crashing."""
        assert capitalize_words("hello2 world!") == "Hello2 World!"

    def test_capitalize_none_input_raises(self):
        """Verify passing None triggers the falsy-check branch and returns empty string safely."""
        assert capitalize_words(None) == ""

    def test_capitalize_injection_like_input_safe(self):
        """Verify injection-like payload is only capitalized as plain text, not executed or altered maliciously."""
        payload = "<script>alert('xss')</script> test"
        result = capitalize_words(payload)
        assert result.startswith("<script>alert('xss')</script>")
        assert "Test" in result


class TestTruncate:
    def test_truncate_no_truncation_needed(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_exact_length(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipses."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_text_appends_ellipsis(self):
        """Verify text longer than max_length is truncated and ellipses appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_zero_max_length_raises(self):
        """Verify max_length of zero raises ValueError (boundary condition)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises(self):
        """Verify negative max_length raises ValueError, preventing invalid slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text(self):
        """Verify truncating an empty string with a positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation works correctly at the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_long_injection_payload(self):
        """Verify a long malicious payload string is safely truncated without code execution."""
        payload = "<script>" + "a" * 100 + "</script>"
        result = truncate(payload, 8)
        assert result == "<script..."
        assert len(result) == 8 + 3

    def test_truncate_non_int_max_length_raises(self):
        """Verify a non-integer max_length that cannot be compared raises TypeError."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
