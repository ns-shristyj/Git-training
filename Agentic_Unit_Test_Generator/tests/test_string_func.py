import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_basic_string(self):
        """Verifies basic string reversal works correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verifies reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_with_spaces(self):
        """Verifies reversal preserves and reverses whitespace correctly."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_special_characters(self):
        """Verifies reversal handles special/injection-like characters safely without executing them."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Ensure no code execution artifacts occur; result is just a string
        assert isinstance(result, str)

    def test_reverse_unicode_string(self):
        """Verifies reversal handles unicode characters correctly."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_non_string_raises_type_error(self):
        """Verifies passing a non-string type raises a TypeError instead of corrupting output."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_capitalize_basic_sentence(self):
        """Verifies each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string_returns_empty(self):
        """Verifies an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_none_returns_empty(self):
        """Verifies falsy input like None is safely handled and returns empty string."""
        assert capitalize_words(None) == ""

    def test_capitalize_single_word(self):
        """Verifies a single word is properly capitalized."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_already_capitalized(self):
        """Verifies already-capitalized words remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_mixed_case_words(self):
        """Verifies mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verifies multiple whitespace separators are collapsed via split/join."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verifies leading and trailing whitespace is stripped from result."""
        assert capitalize_words("   hello world   ") == "Hello World"

    def test_capitalize_numeric_and_special_words(self):
        """Verifies words containing numbers or symbols are handled without crashing."""
        assert capitalize_words("123abc test-word") == "123abc Test-word"

    def test_capitalize_injection_payload_safe(self):
        """Verifies script-like payload words are treated as plain text without execution."""
        result = capitalize_words("<script>alert(1)</script> test")
        assert result == "<script>alert(1)</script> Test"
        assert isinstance(result, str)


class TestTruncate:
    def test_truncate_shorter_than_max_returns_original(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_returns_original(self):
        """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_appends_ellipsis(self):
        """Verifies text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_zero_max_length_raises_value_error(self):
        """Verifies max_length of zero raises ValueError instead of producing invalid output."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verifies negative max_length raises ValueError to prevent malformed truncation."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_with_positive_max(self):
        """Verifies truncating an empty string with valid max_length returns empty string."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies boundary case where max_length is 1 correctly truncates with ellipsis."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_input_does_not_crash(self):
        """Verifies truncate handles very large input strings without performance/crash issues."""
        long_text = "a" * 1_000_000
        result = truncate(long_text, 10)
        assert result == "a" * 10 + "..."

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_various_non_positive_lengths_raise(self, max_length):
        """Verifies all non-positive max_length values consistently raise ValueError."""
        with pytest.raises(ValueError):
            truncate("some text", max_length)
