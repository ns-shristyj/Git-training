import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_basic_reversal(self):
        """Verifies that a simple string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_empty_string(self):
        """Verifies that reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_single_character(self):
        """Verifies that a single character string reverses to itself."""
        assert reverse_string("a") == "a"

    def test_palindrome(self):
        """Verifies that a palindrome remains unchanged after reversal."""
        assert reverse_string("racecar") == "racecar"

    def test_string_with_spaces(self):
        """Verifies that spaces are preserved and reversed along with other characters."""
        assert reverse_string("a b c") == "c b a"

    def test_unicode_characters(self):
        """Verifies that unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_special_characters_are_not_interpreted(self):
        """Verifies that special/injection-like characters are treated as plain data and reversed safely."""
        payload = "'; DROP TABLE users; --"
        expected = payload[::-1]
        assert reverse_string(payload) == expected

    def test_path_traversal_string_treated_as_data(self):
        """Verifies that a path traversal string is simply reversed as text, not interpreted as a path."""
        payload = "../../etc/passwd"
        assert reverse_string(payload) == "dwssap/cte/../.."

    def test_non_string_input_raises_type_error(self):
        """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(123)


class TestCapitalizeWords:
    def test_basic_capitalization(self):
        """Verifies that each word's first letter is capitalized and rest lowercased."""
        assert capitalize_words("hello world") == "Hello World"

    def test_empty_string_returns_empty(self):
        """Verifies that an empty string input returns an empty string."""
        assert capitalize_words("") == ""

    def test_none_like_falsy_short_circuit(self):
        """Verifies that falsy input (empty string) short-circuits before split/join logic."""
        assert capitalize_words("") == ""

    def test_already_capitalized_words(self):
        """Verifies that already capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_all_uppercase_words_are_normalized(self):
        """Verifies that all-uppercase words are converted to capitalized form (first letter upper, rest lower)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_multiple_spaces_collapsed(self):
        """Verifies that multiple spaces between words are collapsed by split()/join()."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_leading_and_trailing_whitespace_stripped(self):
        """Verifies that leading/trailing whitespace is removed due to split() behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_single_word(self):
        """Verifies that a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_whitespace_only_string_returns_empty(self):
        """Verifies that a string containing only whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_numbers_and_symbols_in_words(self):
        """Verifies that words containing numbers or symbols are capitalized safely without error."""
        assert capitalize_words("hello123 world!") == "Hello123 World!"

    def test_injection_like_input_treated_as_plain_text(self):
        """Verifies that injection-like payloads are treated as plain words, not executed or interpreted."""
        payload = "<script>alert(1)</script> test"
        result = capitalize_words(payload)
        assert result == "<script>alert(1)</script> Test"

    def test_non_string_input_raises_type_error(self):
        """Verifies that passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            capitalize_words(123)


class TestTruncate:
    def test_text_shorter_than_max_length_unchanged(self):
        """Verifies that text shorter than max_length is returned unchanged with no ellipsis."""
        assert truncate("hello", 10) == "hello"

    def test_text_equal_to_max_length_unchanged(self):
        """Verifies that text exactly equal to max_length is returned unchanged with no ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_text_longer_than_max_length_truncated_with_ellipsis(self):
        """Verifies that text longer than max_length is truncated and appended with ellipsis."""
        assert truncate("hello world", 5) == "hello..."

    def test_empty_string_input(self):
        """Verifies that an empty string input with a positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_max_length_zero_raises_value_error(self):
        """Verifies that a max_length of zero raises ValueError, preventing invalid boundary configuration."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_negative_max_length_raises_value_error(self):
        """Verifies that a negative max_length raises ValueError, blocking invalid/adversarial input."""
        with pytest.raises(ValueError):
            truncate("hello", -1)

    def test_max_length_one(self):
        """Verifies correct truncation behavior at the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_large_max_length_no_truncation(self):
        """Verifies that a very large max_length does not truncate a short string."""
        assert truncate("hi", 1000000) == "hi"

    def test_non_string_max_length_raises_type_error(self):
        """Verifies that a non-integer max_length raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_long_injection_like_string_truncated_safely(self):
        """Verifies that a malicious long payload is truncated safely without executing or expanding it."""
        payload = "<script>" + "a" * 100 + "</script>"
        result = truncate(payload, 8)
        assert result == "<script..."
        assert len(result) == 11
