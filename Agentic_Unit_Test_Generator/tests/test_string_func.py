import pytest
from NIC_SecEng_Task.Calculator.string_func import reverse_string, capitalize_words, truncate


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verify a simple ASCII string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verify reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verify reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify a palindrome reverses to itself."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verify strings with spaces reverse correctly, preserving spaces."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_string_with_special_characters(self):
        """Verify special characters (e.g. injection-like payloads) are reversed but not executed or altered semantically."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # ensure it's just reversed text, not executed or interpreted
        assert result != payload

    def test_reverse_string_unicode(self):
        """Verify unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_newlines(self):
        """Verify strings containing newline characters are reversed safely."""
        assert reverse_string("a\nb") == "b\na"

    def test_reverse_non_string_raises_type_error(self):
        """Verify passing a non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify an empty string returns an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_input(self):
        """Verify falsy input (empty string) is handled without exceptions."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verify already capitalized words remain properly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case(self):
        """Verify mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verify extra whitespace between words is collapsed by split/join behavior."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verify leading and trailing whitespace is stripped by split/join behavior."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_single_word(self):
        """Verify a single word is capitalized correctly."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_whitespace_only_string(self):
        """Verify a string of only whitespace returns an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_with_numbers_and_symbols(self):
        """Verify words containing numbers/symbols are capitalized without crashing."""
        assert capitalize_words("hello123 world!") == "Hello123 World!"

    def test_capitalize_injection_like_payload(self):
        """Verify potentially malicious payload text is treated as plain data, not executed."""
        payload = "'; drop table users; --"
        result = capitalize_words(payload)
        assert "DROP" not in result.upper() or result == "'; Drop Table Users; --"
        # main assertion: function only transforms text, doesn't execute or alter structure unexpectedly
        assert isinstance(result, str)

    def test_capitalize_non_string_raises_error(self):
        """Verify non-string input raises an appropriate error rather than corrupting behavior."""
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
        """Verify text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_one(self):
        """Verify truncation works correctly with the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_zero_max_length_raises_value_error(self):
        """Verify max_length of zero raises ValueError (boundary condition)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify negative max_length raises ValueError to prevent invalid slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_positive_max_length(self):
        """Verify truncating an empty string with a valid positive max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_with_special_characters(self):
        """Verify truncation of strings containing special/injection-like characters does not execute payload, only slices text."""
        payload = "<script>alert(1)</script>"
        result = truncate(payload, 8)
        assert result == "<script..."
        assert "alert(1)" not in result

    def test_truncate_large_max_length_no_ellipsis(self):
        """Verify a max_length far larger than text length returns text unchanged without ellipsis."""
        assert truncate("hi", 1000) == "hi"

    def test_truncate_non_string_text_raises_type_error(self):
        """Verify non-string text input raises TypeError rather than producing unexpected output."""
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_truncate_non_int_max_length_raises_error(self):
        """Verify non-integer max_length raises an error instead of silently misbehaving."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
