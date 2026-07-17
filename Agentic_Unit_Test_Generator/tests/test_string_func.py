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

    def test_reverse_string_with_script_payload(self):
        """Verify a script-injection-like payload is only textually reversed, not executed or interpreted."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload
        assert "<script>" not in result

    def test_reverse_string_with_sql_payload(self):
        """Verify a SQL-injection-like payload is reversed as plain text without special handling."""
        payload = "'; DROP TABLE users; --"
        result = reverse_string(payload)
        assert result == payload[::-1]

    def test_reverse_string_unicode(self):
        """Verify unicode characters are reversed correctly without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_newlines(self):
        """Verify strings containing newline characters are reversed safely."""
        assert reverse_string("a\nb") == "b\na"

    def test_reverse_string_with_null_byte(self):
        """Verify strings containing a null byte are reversed without truncation or crash."""
        payload = "abc\x00def"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert "\x00" in result

    def test_reverse_non_string_int_raises_type_error(self):
        """Verify passing an integer raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)

    def test_reverse_non_string_none_raises_type_error(self):
        """Verify passing None raises a TypeError rather than returning an unexpected value."""
        with pytest.raises(TypeError):
            reverse_string(None)

    def test_reverse_non_string_list_raises_type_error(self):
        """Verify passing a list raises a TypeError instead of reversing the list silently as if it were valid input text."""
        with pytest.raises(TypeError):
            reverse_string(["a", "b", "c"])


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verify each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verify an empty string returns an empty string."""
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

    def test_capitalize_sql_injection_payload_treated_as_text(self):
        """Verify a SQL-injection-like payload is only capitalized as text and not treated as executable structure."""
        payload = "'; drop table users; --"
        result = capitalize_words(payload)
        assert isinstance(result, str)
        assert result == "'; Drop Table Users; --"

    def test_capitalize_non_string_int_raises_error(self):
        """Verify integer input raises an AttributeError rather than corrupting behavior."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)

    def test_capitalize_non_string_none_raises_error(self):
        """Verify None input raises an AttributeError rather than crashing unexpectedly elsewhere."""
        with pytest.raises(AttributeError):
            capitalize_words(None)

    def test_capitalize_with_tabs_and_newlines(self):
        """Verify whitespace characters like tabs and newlines are treated as word separators safely."""
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"


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
        """Verify max_length of zero raises ValueError as a boundary condition guard."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify negative max_length raises ValueError to prevent invalid slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_positive_max_length(self):
        """Verify truncating an empty string with a valid positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_script_payload_does_not_leak_full_payload(self):
        """Verify truncation of a script-injection-like payload cuts off the executable portion safely."""
        payload = "<script>alert(1)</script>"
        result = truncate(payload, 8)
        assert result == "<script..."
        assert "alert(1)" not in result

    def test_truncate_path_traversal_payload_is_only_sliced_text(self):
        """Verify a path-traversal-like payload is treated as plain text and merely sliced, not resolved as a path."""
        payload = "../../../../etc/passwd"
        result = truncate(payload, 5)
        assert result == "../.." + "..."
        assert not result.endswith("passwd")

    def test_truncate_large_max_length_no_ellipsis(self):
        """Verify a max_length far larger than text length returns text unchanged without ellipsis."""
        assert truncate("hi", 1000) == "hi"

    def test_truncate_non_string_text_raises_type_error(self):
        """Verify non-string text input raises TypeError rather than producing unexpected output."""
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_truncate_non_int_max_length_raises_error(self):
        """Verify a string max_length raises a TypeError instead of silently misbehaving via string comparison."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_none_max_length_raises_error(self):
        """Verify None as max_length raises a TypeError rather than bypassing length validation."""
        with pytest.raises(TypeError):
            truncate("hello", None)
