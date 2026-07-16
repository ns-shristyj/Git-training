import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify a simple ASCII string is correctly reversed."""
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
        """Verify a string with spaces reverses including whitespace positions."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_string(self):
        """Verify unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_characters(self):
        """Verify special/injection-like characters are reversed safely as plain text data."""
        text = "<script>alert(1)</script>"
        result = reverse_string(text)
        assert result == text[::-1]
        # ensure no execution/interpretation occurs, just data reversal
        assert result[::-1] == text

    def test_reverse_string_type_error_on_non_string(self):
        """Verify passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word in a simple sentence is capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify an empty string input returns an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_none_input_treated_as_falsy(self):
        """Verify passing None (falsy) returns empty string due to explicit check."""
        assert capitalize_words(None) == ""

    def test_capitalize_already_capitalized_words(self):
        """Verify words that are already capitalized remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case_words(self):
        """Verify mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLO wORLD") == "Hello World"

    def test_capitalize_collapses_multiple_spaces(self):
        """Verify multiple whitespace separators are collapsed to single spaces via split/join."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_string_with_only_whitespace(self):
        """Verify a string containing only whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_single_word(self):
        """Verify a single word input is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_words_with_numbers(self):
        """Verify words containing numbers are not altered incorrectly."""
        assert capitalize_words("test123 abc456") == "Test123 Abc456"

    def test_capitalize_words_with_leading_trailing_whitespace(self):
        """Verify leading/trailing whitespace is stripped due to split() behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_injection_like_input_is_safe_text(self):
        """Verify injection-like payload is only capitalized as plain text, not executed/interpreted."""
        payload = "'; drop table users; --"
        result = capitalize_words(payload)
        assert "Drop" in result
        assert "Table" in result

    def test_capitalize_words_type_error_on_non_string(self):
        """Verify passing a non-string, non-None truthy type raises AttributeError/TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            capitalize_words(12345)


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verify text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verify text exactly equal to max_length is returned without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verify text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_zero_max_length_raises_value_error(self):
        """Verify max_length of zero raises ValueError as required by input validation."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify negative max_length raises ValueError, preventing invalid boundary usage."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_with_positive_max_length(self):
        """Verify an empty string input with valid max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation to length one correctly slices and appends ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_max_length_no_truncation(self):
        """Verify a very large max_length never truncates the input text."""
        text = "short text"
        assert truncate(text, 10_000) == text

    def test_truncate_does_not_execute_embedded_payload(self):
        """Verify potentially malicious payload text is only truncated as data, not executed."""
        payload = "<img src=x onerror=alert(1)>" * 3
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert result.endswith("...")

    def test_truncate_max_length_type_error_on_non_int(self):
        """Verify passing a non-integer max_length raises TypeError instead of unsafe comparison."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
