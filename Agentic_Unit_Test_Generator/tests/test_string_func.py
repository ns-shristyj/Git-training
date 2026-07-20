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

    def test_single_character(self):
        """Verifies reversing a single character string returns the same character."""
        assert reverse_string("a") == "a"

    def test_palindrome(self):
        """Verifies reversing a palindrome returns the same string."""
        assert reverse_string("madam") == "madam"

    def test_reverse_with_spaces(self):
        """Verifies reversal preserves and reverses spaces correctly."""
        assert reverse_string("a b c") == "c b a"

    def test_reverse_unicode_characters(self):
        """Verifies reversal handles unicode characters safely without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_injection_like_payload_is_inert(self):
        """Verifies that script-injection-like payloads are only reversed as plain text, not executed or altered."""
        payload = "<script>alert(1)</script>"
        result = reverse_string(payload)
        assert result == payload[::-1]
        assert "<script>" not in result

    def test_reverse_path_traversal_string_is_inert(self):
        """Verifies path traversal-like strings are safely reversed as plain text with no filesystem interaction."""
        payload = "../../../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]

    def test_reverse_non_string_raises_type_error(self):
        """Verifies that passing a non-subscriptable, non-string type raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_basic_capitalization(self):
        """Verifies basic capitalization of each word in a sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_empty_string_returns_empty(self):
        """Verifies empty string input returns empty string without error."""
        assert capitalize_words("") == ""

    def test_none_input_returns_empty(self):
        """Verifies that None input is treated as falsy and returns empty string safely."""
        assert capitalize_words(None) == ""

    def test_already_capitalized_words(self):
        """Verifies already capitalized words remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_all_uppercase_words_lowercased_except_first_letter(self):
        """Verifies all-uppercase words are normalized to capitalized form."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_multiple_spaces_collapsed(self):
        """Verifies multiple whitespace separators between words are collapsed to single spaces."""
        assert capitalize_words("hello    world") == "Hello World"

    def test_leading_trailing_whitespace_stripped(self):
        """Verifies leading and trailing whitespace is stripped by split/join behavior."""
        assert capitalize_words("   hello world   ") == "Hello World"

    def test_single_word(self):
        """Verifies capitalization works correctly on a single word."""
        assert capitalize_words("python") == "Python"

    def test_whitespace_only_string_returns_empty(self):
        """Verifies a string consisting only of whitespace returns an empty string."""
        assert capitalize_words("   ") == ""

    def test_capitalize_injection_like_payload_is_inert(self):
        """Verifies script-injection-like text is only capitalized as plain text without execution."""
        result = capitalize_words("<script>alert(1)</script> hello")
        assert "Hello" in result
        assert "<script>alert(1)</script>".capitalize() in result

    def test_non_string_truthy_input_raises_attribute_error(self):
        """Verifies that a truthy non-string input (lacking a split method) raises an AttributeError rather than being silently mishandled."""
        with pytest.raises(AttributeError):
            capitalize_words(12345)


class TestTruncate:
    def test_no_truncation_needed(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_exact_length_no_ellipsis(self):
        """Verifies text exactly equal to max_length is returned without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncation_with_ellipsis(self):
        """Verifies text longer than max_length is truncated and ellipsis is appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_max_length_zero_raises_value_error(self):
        """Verifies max_length of zero raises a ValueError to prevent invalid boundary usage."""
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_negative_max_length_raises_value_error(self):
        """Verifies negative max_length raises a ValueError instead of producing unexpected slicing behavior."""
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_empty_text_with_positive_max_length(self):
        """Verifies empty text input with a valid max_length returns an empty string."""
        assert truncate("", 5) == ""

    def test_max_length_one(self):
        """Verifies truncation works correctly for the minimal positive max_length boundary."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_large_input_does_not_crash(self):
        """Verifies truncation safely handles very large input strings without performance/memory failure."""
        large_text = "a" * 1_000_000
        result = truncate(large_text, 100)
        assert result == "a" * 100 + "..."

    def test_truncate_injection_like_payload_is_inert(self):
        """Verifies script-injection-like payloads are truncated as plain text without execution."""
        payload = "<script>alert('xss')</script>" * 5
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."

    def test_truncate_path_traversal_payload_is_inert(self):
        """Verifies path traversal-like payloads are truncated as plain text with no filesystem interaction."""
        payload = "../" * 100 + "etc/passwd"
        result = truncate(payload, 20)
        assert result == payload[:20] + "..."

    @pytest.mark.parametrize("bad_max_length", [0, -1, -100])
    def test_various_non_positive_max_lengths_raise_value_error(self, bad_max_length):
        """Verifies all non-positive max_length boundary values consistently raise ValueError."""
        with pytest.raises(ValueError):
            truncate("some text", bad_max_length)

    def test_non_string_text_raises_type_error(self):
        """Verifies that passing a non-string text type raises a TypeError when its length cannot be determined."""
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_non_integer_max_length_raises_type_error(self):
        """Verifies that passing a non-integer max_length raises a TypeError due to incompatible comparison with an integer."""
        with pytest.raises(TypeError):
            truncate("hello", "5")
