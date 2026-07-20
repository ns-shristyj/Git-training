import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_normal_string(self):
        """Verifies a standard string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verifies reversing a single character string returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_with_spaces(self):
        """Verifies string with spaces is reversed correctly including whitespace."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_with_special_characters(self):
        """Verifies string with special/injection-like characters is reversed safely without execution."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure it remains inert data, not executed or altered semantically
        assert "script" in result

    def test_reverse_unicode_string(self):
        """Verifies unicode characters are reversed correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_numeric_string(self):
        """Verifies numeric strings are reversed correctly."""
        assert reverse_string("12345") == "54321"

    def test_reverse_non_string_raises_type_error(self):
        """Verifies passing a non-string type raises a TypeError due to unsupported slicing operation."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verifies a single lowercase word is capitalized correctly."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verifies each word in a multi-word string is capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verifies an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verifies already capitalized words remain correctly capitalized (mixed case normalized)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_normalized(self):
        """Verifies extra whitespace between words is collapsed by split/join behavior."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verifies a string containing only whitespace returns an empty string since split() yields no words."""
        assert capitalize_words("   ") == ""

    def test_capitalize_mixed_case_words(self):
        """Verifies mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLo wORLd") == "Hello World"

    def test_capitalize_words_with_numbers(self):
        """Verifies words containing numbers are handled without crashing."""
        assert capitalize_words("123abc def456") == "123abc Def456"

    def test_capitalize_single_character_words(self):
        """Verifies single-character words are capitalized correctly."""
        assert capitalize_words("a b c") == "A B C"

    def test_capitalize_none_input_returns_empty_string(self):
        """Verifies passing None is treated as falsy and returns an empty string rather than raising an error."""
        assert capitalize_words(None) == ""

    def test_capitalize_non_string_raises_attribute_error(self):
        """Verifies passing a truthy non-string type raises AttributeError since split() is not supported."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)


class TestTruncate:
    def test_truncate_text_shorter_than_max_length(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_text_equal_to_max_length(self):
        """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_text_longer_than_max_length(self):
        """Verifies text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_empty_string(self):
        """Verifies an empty string with positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    @pytest.mark.parametrize("max_length", [-1000, -5, -1, 0])
    def test_truncate_various_non_positive_lengths_raise_value_error(self, max_length):
        """Verifies a range of non-positive max_length values are all safely rejected via ValueError."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)

    def test_truncate_max_length_one(self):
        """Verifies truncation with max_length of 1 produces a single character plus ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_non_integer_max_length_raises_type_error(self):
        """Verifies a non-integer max_length that fails comparison raises TypeError, avoiding silent misbehavior."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_large_input_does_not_crash(self):
        """Verifies truncation of a very large string does not crash and returns correct truncated form."""
        large_text = "a" * 100000
        result = truncate(large_text, 50)
        assert result == "a" * 50 + "..."
        assert len(result) == 53

    def test_truncate_with_injection_like_payload(self):
        """Verifies truncation safely handles injection-like payloads without executing or altering them beyond truncation."""
        payload = "<script>alert('xss')</script>" * 10
        result = truncate(payload, 20)
        assert result == payload[:20] + "..."
        assert result.startswith("<script>")
