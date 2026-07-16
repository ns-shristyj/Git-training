import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_normal_string(self):
        """Verifies a basic string is reversed correctly."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_char(self):
        """Verifies reversing a single character string returns itself."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_string_with_spaces(self):
        """Verifies reversing preserves whitespace correctly in reversed order."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_string_with_unicode(self):
        """Verifies reversing handles unicode characters without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_string_with_special_chars(self):
        """Verifies reversing handles injection-like special characters safely as plain data."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert result != payload

    def test_reverse_string_with_newlines_and_tabs(self):
        """Verifies reversing handles newline and tab characters without error."""
        text = "a\nb\tc"
        assert reverse_string(text) == "c\tb\na"


class TestCapitalizeWords:
    def test_capitalize_basic_sentence(self):
        """Verifies each word in a simple sentence is capitalized."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verifies an empty string input returns an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verifies already capitalized words remain properly capitalized (lowercase rest)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_single_word(self):
        """Verifies a single lowercase word is capitalized."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_multiple_spaces_collapsed(self):
        """Verifies multiple spaces between words are collapsed to single spaces."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_capitalize_leading_trailing_whitespace(self):
        """Verifies leading and trailing whitespace is stripped in output."""
        assert capitalize_words("  hello world  ") == "Hello World"

    def test_capitalize_only_whitespace(self):
        """Verifies a string consisting only of whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_mixed_case_words(self):
        """Verifies mixed case words are normalized to capitalized form."""
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_capitalize_numbers_and_words(self):
        """Verifies numeric tokens are preserved without alteration and words capitalized."""
        assert capitalize_words("123 hello") == "123 Hello"

    def test_capitalize_with_special_characters(self):
        """Verifies special characters within a word do not raise errors and are handled as text."""
        result = capitalize_words("hello-world foo_bar")
        assert result == "Hello-world Foo_bar"

    def test_capitalize_newline_and_tab_separated(self):
        """Verifies words separated by tabs/newlines are split and capitalized correctly."""
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"


class TestTruncate:
    def test_truncate_shorter_than_max_length(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length(self):
        """Verifies text exactly equal to max_length is returned unchanged without ellipses."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length(self):
        """Verifies text longer than max_length is truncated and ellipses appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises(self):
        """Verifies max_length of zero raises ValueError as per positive-integer validation."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises(self):
        """Verifies negative max_length raises ValueError, preventing invalid boundary behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_string_with_positive_max_length(self):
        """Verifies truncating an empty string returns an empty string when max_length is positive."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies boundary case where max_length is 1 and text exceeds it."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_long_injection_like_payload(self):
        """Verifies truncation safely cuts off a long malicious-looking payload without executing it."""
        payload = "<script>" + "a" * 100 + "</script>"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert len(result) == 13
