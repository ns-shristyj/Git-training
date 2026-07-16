import pytest
from NIC_SecEng_Task.Calculator.string_func import reverse_string, capitalize_words, truncate


class TestReverseString:
    def test_reverse_simple_word(self):
        """Verifies basic reversal of a simple word."""
        assert reverse_string("hello") == "olleh"

    def test_reverse_empty_string(self):
        """Verifies reversing an empty string returns an empty string."""
        assert reverse_string("") == ""

    def test_reverse_single_character(self):
        """Verifies reversing a single character returns the same character."""
        assert reverse_string("a") == "a"

    def test_reverse_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("racecar") == "racecar"

    def test_reverse_sentence_with_spaces(self):
        """Verifies reversal correctly handles spaces within a sentence."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_unicode_characters(self):
        """Verifies reversal correctly handles unicode/multi-byte characters."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_special_characters(self):
        """Verifies reversal safely handles special/injection-like characters without crashing."""
        text = "<script>alert(1)</script>"
        result = reverse_string(text)
        assert result == text[::-1]
        # Ensure the reversed text does not accidentally execute or get altered beyond reversal.
        assert result != text or text == text[::-1]

    def test_reverse_newlines_and_tabs(self):
        """Verifies reversal handles strings containing newline and tab characters."""
        text = "a\nb\tc"
        assert reverse_string(text) == "c\tb\na"


class TestCapitalizeWords:
    def test_capitalize_empty_string(self):
        """Verifies that an empty string returns an empty string."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_input(self):
        """Verifies that a falsy string input triggers the empty-string branch."""
        assert capitalize_words("") == ""

    def test_capitalize_single_word(self):
        """Verifies capitalization of a single lowercase word."""
        assert capitalize_words("hello") == "Hello"

    def test_capitalize_multiple_words(self):
        """Verifies capitalization of each word in a multi-word string."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_already_capitalized(self):
        """Verifies words already capitalized remain correctly capitalized (lowercases rest)."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_mixed_case_words(self):
        """Verifies mixed-case words are normalized to capitalized form."""
        assert capitalize_words("hELLo wORLd") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verifies extra whitespace between words is collapsed due to split()/join() behavior."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_whitespace_only_string(self):
        """Verifies a whitespace-only string returns an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_single_character_words(self):
        """Verifies single-character words are capitalized correctly."""
        assert capitalize_words("a b c") == "A B C"

    def test_capitalize_numeric_and_special_chars(self):
        """Verifies words containing numbers/special characters do not crash the function."""
        result = capitalize_words("123abc test!")
        assert result == "123abc Test!"

    def test_capitalize_injection_like_input(self):
        """Verifies script-like injection input is processed safely as plain text, not executed."""
        text = "<script>alert(1)</script> test"
        result = capitalize_words(text)
        assert result.startswith("<script>alert(1)</script>".capitalize())
        assert "<script>" in result  # confirms it's treated as literal text, not sanitized/executed


class TestTruncate:
    def test_truncate_shorter_than_max_length(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length(self):
        """Verifies text exactly equal to max_length is returned unchanged."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length(self):
        """Verifies text longer than max_length is truncated and ellipses appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_max_length_zero_raises_value_error(self):
        """Verifies that a max_length of zero raises ValueError (boundary condition)."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_truncate_negative_max_length_raises_value_error(self):
        """Verifies that a negative max_length raises ValueError, preventing invalid slicing."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_truncate_empty_text_with_valid_max_length(self):
        """Verifies truncating an empty string returns an empty string when max_length is positive."""
        assert truncate("", 5) == ""

    def test_truncate_max_length_one(self):
        """Verifies truncation works correctly with the smallest valid positive max_length."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_max_length_boundary(self):
        """Verifies text is unmodified when max_length greatly exceeds text length."""
        assert truncate("hi", 1000) == "hi"

    def test_truncate_injection_like_payload(self):
        """Verifies path-traversal/injection-like payload text is truncated safely without special handling bypass."""
        payload = "../../../etc/passwd" * 3
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        assert len(result) == 13
