import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_string_happy_path(self):
        """Basic sanity check: reverse a normal string."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_string_empty(self):
        """Empty string should return empty string."""
        assert reverse_string("") == ""

    def test_reverse_string_single_char(self):
        """Single character should return itself."""
        assert reverse_string("a") == "a"

    def test_reverse_string_with_spaces(self):
        """String with spaces should reverse including spaces."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_string_unicode(self):
        """Unicode characters should reverse correctly."""
        assert reverse_string("café") == "éfac"

    def test_reverse_string_rtl_override(self):
        """Right-to-left override character should be reversed."""
        rtl_text = "hello\u202eworld"
        assert reverse_string(rtl_text) == "dlrow\u202eolleh"

    def test_reverse_string_null_byte(self):
        """Null byte in string should be reversed."""
        assert reverse_string("hello\x00world") == "dlrow\x00olleh"

    def test_reverse_string_type_error(self):
        """Non-string input should raise TypeError."""
        with pytest.raises(TypeError):
            reverse_string(123)


class TestCapitalizeWords:
    def test_capitalize_words_happy_path(self):
        """Basic sanity check: capitalize words in a normal string."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_words_empty(self):
        """Empty string should return empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_words_single_word(self):
        """Single word should be capitalized."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_words_already_capitalized(self):
        """Already capitalized words should remain capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_words_multiple_spaces(self):
        """Multiple spaces between words should be normalized to single space."""
        assert capitalize_words("hello  world") == "Hello World"

    def test_capitalize_words_unicode(self):
        """Unicode characters should capitalize correctly."""
        assert capitalize_words("café naïve") == "Café Naïve"

    def test_capitalize_words_type_error(self):
        """Non-string input should raise TypeError."""
        with pytest.raises(TypeError):
            capitalize_words(123)


class TestTruncate:
    def test_truncate_happy_path(self):
        """Basic sanity check: truncate a string that exceeds max_length."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_within_limit(self):
        """String within max_length should return unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_exact_length(self):
        """String exactly at max_length should return unchanged."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_empty_string(self):
        """Empty string should return empty string."""
        assert truncate("", 5) == ""

    def test_truncate_single_char(self):
        """Single character within limit should return unchanged."""
        assert truncate("a", 1) == "a"

    def test_truncate_single_char_exceeded(self):
        """Single character exceeding limit should be truncated with ellipses."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_zero_length(self):
        """max_length of 0 should raise ValueError."""
        with pytest.raises(ValueError, match="Maximum length must be a positive integer"):
            truncate("hello", 0)

    def test_truncate_negative_length(self):
        """Negative max_length should raise ValueError."""
        with pytest.raises(ValueError, match="Maximum length must be a positive integer"):
            truncate("hello", -5)

    def test_truncate_unicode(self):
        """Unicode characters should truncate correctly."""
        assert truncate("café naïve", 4) == "café..."

    def test_truncate_oversized_input(self):
        """Very large input should truncate without performance issues."""
        large_text = "a" * 100000
        result = truncate(large_text, 10)
        assert result == "a" * 10 + "..."
        assert len(result) == 13

    def test_truncate_sql_injection_payload(self):
        """SQL injection payload should be truncated like any other string."""
        payload = "' OR 1=1--"
        result = truncate(payload, 5)
        assert result == "' OR ..."

    def test_truncate_path_traversal_payload(self):
        """Path traversal payload should be truncated like any other string."""
        payload = "../../../etc/passwd"
        result = truncate(payload, 5)
        assert result == "../..."

    def test_truncate_type_error_text(self):
        """Non-string text input should raise TypeError."""
        with pytest.raises(TypeError):
            truncate(123, 5)

    def test_truncate_type_error_max_length(self):
        """Non-integer max_length should raise TypeError."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
