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

    def test_reverse_single_char(self):
        """Verify reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verify reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_numeric_string(self):
        """Verify a numeric string is reversed character by character, not treated as a number."""
        assert reverse_string("12345") == "54321"

    def test_reverse_unicode_string(self):
        """Verify reversing a string with unicode characters preserves and reverses each character."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_whitespace_preserved(self):
        """Verify whitespace characters are preserved in position after reversal."""
        assert reverse_string("a b") == "b a"

    def test_reverse_sql_injection_payload_not_executed(self):
        """Verify an SQL-injection-like payload is only reversed and never interpreted or executed."""
        payload = "'; DROP TABLE users; --"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert "DROP TABLE" not in result

    def test_reverse_path_traversal_payload_not_resolved(self):
        """Verify a path-traversal-like string is safely reversed as plain text, not resolved as a path."""
        payload = "../../../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != "/etc/passwd"

    def test_reverse_null_byte_payload_handled_as_text(self):
        """Verify a string containing a null byte is reversed safely without truncation or crash."""
        payload = "abc\x00def"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert len(result) == len(payload)

    def test_reverse_string_type_error_on_int(self):
        """Verify passing an integer raises a TypeError since integers are not subscriptable/sliceable."""
        with pytest.raises(TypeError):
            reverse_string(12345)

    def test_reverse_string_type_error_on_none(self):
        """Verify passing None raises a TypeError instead of silently failing."""
        with pytest.raises(TypeError):
            reverse_string(None)

    def test_reverse_string_type_error_on_list(self):
        """Verify passing a list raises a TypeError since reversing a list is not the same as reversing a string."""
        with pytest.raises(TypeError):
            reverse_string(["a", "b", "c"])

    def test_reverse_string_type_error_on_dict(self):
        """Verify passing a dict raises a TypeError since it is not string-sliceable."""
        with pytest.raises(TypeError):
            reverse_string({"key": "value"})


class TestCapitalizeWords:
    def test_capitalize_single_word(self):
        """Verify a single lowercase word gets its first letter capitalized."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verify multiple words each get capitalized correctly."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verify an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_all_uppercase_words(self):
        """Verify all-uppercase words are converted to capitalized form (first letter upper, rest lower)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verify extra internal whitespace between words is collapsed by split/join logic."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace_stripped(self):
        """Verify leading and trailing whitespace is stripped in the output."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_whitespace_only_string_returns_empty(self):
        """Verify a whitespace-only string returns an empty string since split() yields no words."""
        assert capitalize_words("   ") == ""

    def test_capitalize_words_with_digits_unaffected(self):
        """Verify words containing digits are capitalized without raising errors or altering digits."""
        assert capitalize_words("hello2world 123abc") == "Hello2world 123abc"

    def test_capitalize_single_character_words(self):
        """Verify single-character words are capitalized correctly."""
        assert capitalize_words("a b c") == "A B C"

    def test_capitalize_html_injection_payload_not_executed(self):
        """Verify an HTML/script injection-like payload is only capitalized as text, never executed."""
        payload = "<script>alert('xss')</script> hello"
        result = capitalize_words(payload)
        assert "<script>alert('xss')</script>".lower() in result.lower()
        assert result.split()[-1] == "Hello"

    def test_capitalize_none_raises_attribute_error(self):
        """Verify passing None raises an AttributeError instead of silently succeeding."""
        with pytest.raises(AttributeError):
            capitalize_words(None)

    def test_capitalize_non_string_int_raises_error(self):
        """Verify passing a non-string integer raises an AttributeError since split() is unavailable on ints."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)

    def test_capitalize_non_string_list_raises_error(self):
        """Verify passing a list raises an AttributeError since lists lack the split() string method."""
        with pytest.raises(AttributeError):
            capitalize_words(["hello", "world"])


class TestTruncate:
    def test_truncate_shorter_than_max_length_unchanged(self):
        """Verify text shorter than max_length is returned unchanged with no ellipsis."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length_unchanged(self):
        """Verify text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length_appends_ellipsis(self):
        """Verify text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verify max_length of zero raises ValueError as a boundary/input validation check."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verify a negative max_length raises ValueError, preventing invalid truncation logic."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_returns_empty(self):
        """Verify truncating an empty string with a positive max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verify truncation with max_length of 1 correctly slices to one character plus ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_input_string_handled_without_dos(self):
        """Verify truncation handles a very large input string quickly and correctly (resource exhaustion boundary)."""
        large_text = "a" * 100000
        result = truncate(large_text, 10)
        assert result == "a" * 10 + "..."

    def test_truncate_script_injection_payload_safely_truncated(self):
        """Verify a script-injection-like payload is safely truncated as plain text, never executed."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 8)
        assert result == payload[:8] + "..."
        assert "</script>" not in result

    def test_truncate_sql_injection_payload_safely_truncated(self):
        """Verify a SQL-injection-like payload is safely truncated as plain text without being interpreted."""
        payload = "'; DROP TABLE users; --"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert "DROP TABLE users" not in result

    def test_truncate_type_error_on_non_string_text(self):
        """Verify passing a non-string text raises a TypeError since len()/slicing require string-like behavior."""
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_truncate_type_error_on_none_text(self):
        """Verify passing None as text raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            truncate(None, 5)

    def test_truncate_type_error_on_non_int_max_length(self):
        """Verify passing a non-integer max_length (e.g., string) raises a TypeError due to comparison/slicing failure."""
        with pytest.raises(TypeError):
            truncate("hello world", "five")

    def test_truncate_type_error_on_none_max_length(self):
        """Verify passing None as max_length raises a TypeError due to invalid comparison with int/len."""
        with pytest.raises(TypeError):
            truncate("hello world", None)
