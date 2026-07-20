import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverses_simple_string(self):
        """Verify a simple ASCII string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverses_empty_string(self):
        """Verify empty string input returns empty string."""
        assert reverse_string("") == ""

    def test_reverses_single_character(self):
        """Verify single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_reverses_palindrome(self):
        """Verify palindrome string is unchanged after reversal."""
        assert reverse_string("racecar") == "racecar"

    def test_reverses_string_with_spaces(self):
        """Verify string with spaces and words reverses whole sequence including spaces."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverses_unicode_string(self):
        """Verify unicode characters are reversed without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverses_string_with_special_characters(self):
        """Verify special/injection-like characters are safely reversed as plain text, not executed."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert isinstance(result, str)

    def test_raises_type_error_on_non_string_input(self):
        """Verify passing a non-sliceable type (int) raises TypeError instead of corrupting output."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalizes_single_word(self):
        """Verify a single lowercase word is capitalized."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalizes_multiple_words(self):
        """Verify each word in a multi-word string is capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_returns_empty_string_for_empty_input(self):
        """Verify empty string input returns empty string via explicit guard."""
        assert capitalize_words("") == ""

    def test_collapses_extra_whitespace(self):
        """Verify multiple/leading/trailing whitespace is collapsed by split()/join()."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalizes_already_uppercase_word(self):
        """Verify an all-uppercase word is normalized to capitalized form (first upper, rest lower)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalizes_mixed_case_word(self):
        """Verify mixed-case word is normalized to capitalized form."""
        assert capitalize_words("hELLo") == "Hello"

    def test_capitalizes_with_numbers_and_symbols(self):
        """Verify words containing numbers/symbols are processed without crashing."""
        result = capitalize_words("hello123 world!")
        assert result == "Hello123 World!"

    def test_capitalizes_string_with_only_whitespace(self):
        """Verify a string consisting only of whitespace returns empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_raises_attribute_error_on_non_string_input(self):
        """Verify passing a non-string input raises AttributeError safely rather than corrupting output."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)


class TestTruncate:
    def test_returns_text_unchanged_when_shorter_than_max_length(self):
        """Verify text shorter than max_length is returned unchanged without ellipses."""
        assert truncate("hello", 10) == "hello"

    def test_returns_text_unchanged_when_equal_to_max_length(self):
        """Verify text exactly equal to max_length is returned unchanged (boundary condition)."""
        assert truncate("hello", 5) == "hello"

    def test_truncates_text_longer_than_max_length(self):
        """Verify text longer than max_length is truncated and ellipses appended."""
        assert truncate("hello world", 5) == "hello..."

    @pytest.mark.parametrize("max_length", [0, -1, -5])
    def test_raises_value_error_on_non_positive_max_length(self, max_length):
        """Verify zero or negative max_length values raise ValueError to prevent invalid slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", max_length)

    def test_truncates_with_max_length_one(self):
        """Verify minimal positive max_length of 1 truncates correctly with ellipses."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_empty_text_returns_empty_string(self):
        """Verify empty text with valid positive max_length returns empty string, no ellipses."""
        assert truncate("", 5) == ""

    def test_truncate_does_not_execute_injection_payload(self):
        """Verify truncation of an injection-like payload only slices text safely without executing or leaking beyond the cut."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 8)
        assert result == "<script>..."
        assert "alert" not in result

    def test_raises_type_error_on_non_integer_max_length(self):
        """Verify passing a non-integer max_length raises TypeError due to invalid comparison."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
