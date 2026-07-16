import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_basic_reverse(self):
        """Verifies basic string reversal works correctly."""
        assert reverse_string("hello") == "olleh"

    def test_empty_string(self):
        """Verifies reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_single_char(self):
        """Verifies reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_with_spaces(self):
        """Verifies reversal preserves and reverses spaces correctly."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode(self):
        """Verifies reversal handles unicode characters correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_special_chars_injection_payload(self):
        """Verifies reversal safely handles special/injection-like characters without executing them."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # ensure the payload is treated as plain data, not evaluated
        assert "alert" not in result.split(">")[0]

    def test_reverse_path_traversal_string(self):
        """Verifies reversal treats path traversal strings as plain data without side effects."""
        payload = "../../../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]

    def test_reverse_non_string_raises(self):
        """Verifies that passing a non-string type raises a TypeError."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_basic_capitalization(self):
        """Verifies each word's first letter is capitalized and rest lowercased."""
        assert capitalize_words("hello world") == "Hello World"

    def test_empty_string(self):
        """Verifies empty string input returns empty string."""
        assert capitalize_words("") == ""

    def test_single_word(self):
        """Verifies single word capitalization works correctly."""
        assert capitalize_words("python") == "Python"

    def test_already_capitalized(self):
        """Verifies already capitalized words remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_mixed_case_input(self):
        """Verifies mixed case words are normalized to capitalized form."""
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_multiple_spaces_collapsed(self):
        """Verifies multiple spaces between words are collapsed by split/join."""
        assert capitalize_words("hello   world") == "Hello World"

    def test_leading_trailing_whitespace(self):
        """Verifies leading and trailing whitespace is stripped in output."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_whitespace_only_string(self):
        """Verifies a string of only whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_numbers_and_words(self):
        """Verifies numeric words remain unchanged when capitalized."""
        assert capitalize_words("123 abc") == "123 Abc"

    def test_none_input(self):
        """Verifies that None input returns empty string due to falsy check."""
        assert capitalize_words(None) == ""

    def test_non_string_type_raises(self):
        """Verifies that a non-string, non-None truthy input raises an AttributeError."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)

    def test_injection_payload_capitalization(self):
        """Verifies capitalization safely processes injection-like strings without executing them."""
        payload = "<script>alert(1)</script> hello"
        result = capitalize_words(payload)
        assert result.startswith("<script>alert(1)</script>".capitalize())
        assert "Hello" in result


class TestTruncate:
    def test_no_truncation_needed(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_exact_length_no_truncation(self):
        """Verifies text exactly equal to max_length is not truncated."""
        assert truncate("hello", 5) == "hello"

    def test_truncation_with_ellipsis(self):
        """Verifies text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_max_length_zero_raises(self):
        """Verifies max_length of zero raises ValueError (boundary condition)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_max_length_negative_raises(self):
        """Verifies negative max_length raises ValueError."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_max_length_one(self):
        """Verifies truncation works correctly with minimal positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_empty_text(self):
        """Verifies empty text input returns empty string regardless of max_length."""
        assert truncate("", 5) == ""

    def test_truncate_large_input_dos_boundary(self):
        """Verifies truncate handles very large input strings without error (DoS-style boundary)."""
        large_text = "a" * 1_000_000
        result = truncate(large_text, 10)
        assert result == "a" * 10 + "..."

    def test_truncate_non_integer_max_length_raises(self):
        """Verifies passing a non-integer max_length raises a TypeError on comparison."""
        with pytest.raises(TypeError):
            truncate("hello world", "5")

    def test_truncate_injection_payload(self):
        """Verifies injection-like payload text is truncated as plain data without execution."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 8)
        assert result == payload[:8] + "..."
        assert "alert(" not in result or result.endswith("...")
