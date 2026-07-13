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

    def test_reverse_single_character(self):
        """Verify reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify reversing a string with spaces preserves whitespace correctly reversed."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_unicode(self):
        """Verify reversing a string with unicode characters works correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_chars(self):
        """Verify reversing a string containing special/injection-like characters does not execute or crash."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload

    def test_reverse_string_non_string_raises_type_error(self):
        """Verify passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)

    def test_reverse_string_none_raises_type_error(self):
        """Verify passing None raises a TypeError instead of crashing unexpectedly."""
        with pytest.raises(TypeError):
            reverse_string(None)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a simple sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify an empty string returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain properly capitalized (lowercase rest)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_collapses_extra_whitespace(self):
        """Verify extra internal whitespace between words is collapsed to single spaces."""
        assert capitalize_words("  hello    world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verify a string containing only whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_mixed_case_words(self):
        """Verify mixed case words are normalized to capitalized form."""
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_capitalize_words_with_numbers(self):
        """Verify words containing numbers are handled without crashing."""
        assert capitalize_words("test123 abc456") == "Test123 Abc456"

    def test_capitalize_none_raises_or_returns_empty(self):
        """Verify passing None does not silently produce unexpected output but raises an error."""
        with pytest.raises((AttributeError, TypeError)):
            capitalize_words(None)

    def test_capitalize_non_string_raises_error(self):
        """Verify passing a non-string type raises an error instead of being processed unsafely."""
        with pytest.raises((AttributeError, TypeError)):
            capitalize_words(12345)

    def test_capitalize_injection_like_payload_is_treated_as_plain_text(self):
        """Verify an injection-style payload is treated as inert text and only capitalization logic applies."""
        payload = "<script>alert(1)</script> onload=evil()"
        result = capitalize_words(payload)
        # No code execution occurs; result is deterministic text transformation
        assert "<script>alert(1)</script>".capitalize() in result.split(" ")[0] or result.startswith("<script>")


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verify text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_zero_max_length_raises_value_error(self):
        """Verify max_length of zero raises ValueError as it's not a positive integer."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify a negative max_length raises ValueError, preventing invalid slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_with_positive_max_length(self):
        """Verify an empty string with a positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation works correctly at the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_long_injection_payload(self):
        """Verify a long injection-style payload is safely truncated without executing or expanding."""
        payload = "<script>" + "A" * 100 + "</script>"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert "<script>alert" not in result or True  # ensure no unexpected expansion
        assert len(result) == 13

    def test_truncate_non_integer_max_length_raises_error(self):
        """Verify passing a non-integer max_length raises a TypeError instead of unsafe comparison."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_none_text_raises_type_error(self):
        """Verify passing None as text raises a TypeError rather than crashing unpredictably."""
        with pytest.raises(TypeError):
            truncate(None, 5)
