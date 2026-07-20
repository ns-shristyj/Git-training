import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_reverse_simple_string(self):
        """Verifies basic string reversal works correctly."""
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

    def test_reverse_with_spaces(self):
        """Verifies reversal correctly handles spaces within text."""
        assert reverse_string("hello world") == "dlrow olleh"

    def test_reverse_with_unicode_characters(self):
        """Verifies reversal safely handles unicode/multi-byte characters without corruption."""
        assert reverse_string("héllo") == "olléh"

    def test_reverse_with_special_characters(self):
        """Verifies reversal safely handles special/injection-like characters as inert data."""
        assert reverse_string("<script>alert(1)</script>") == ">tpircs/<)1(trela>tpircs<"

    def test_reverse_with_newlines_and_tabs(self):
        """Verifies reversal handles control characters like newlines and tabs correctly."""
        assert reverse_string("a\nb\tc") == "c\tb\na"


class TestCapitalizeWords:
    def test_capitalize_simple_sentence(self):
        """Verifies each word's first letter is capitalized in a normal sentence."""
        assert capitalize_words("hello world") == "Hello World"

    def test_capitalize_empty_string(self):
        """Verifies an empty string input returns an empty string without error."""
        assert capitalize_words("") == ""

    def test_capitalize_none_like_falsy_input(self):
        """Verifies falsy string input (empty) is short-circuited safely."""
        assert capitalize_words("") == ""

    def test_capitalize_already_capitalized(self):
        """Verifies already capitalized words remain correctly capitalized."""
        assert capitalize_words("Hello World") == "Hello World"

    def test_capitalize_all_uppercase_words(self):
        """Verifies all-uppercase words are lowered except for first letter."""
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_capitalize_extra_whitespace_collapsed(self):
        """Verifies multiple/extra whitespace between words is collapsed to single spaces."""
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_capitalize_single_word(self):
        """Verifies a single word is correctly capitalized."""
        assert capitalize_words("python") == "Python"

    def test_capitalize_with_numbers_and_symbols(self):
        """Verifies words containing numbers/symbols are handled without crashing."""
        assert capitalize_words("123abc def!") == "123abc Def!"

    def test_capitalize_whitespace_only_string(self):
        """Verifies a whitespace-only string returns an empty string after split/join."""
        assert capitalize_words("   ") == ""

    def test_capitalize_with_tabs_and_newlines_as_separators(self):
        """Verifies tabs and newlines are treated as word separators like whitespace."""
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"


class TestTruncate:
    def test_truncate_shorter_than_max_length(self):
        """Verifies text shorter than max_length is returned unchanged."""
        assert truncate("hello", 10) == "hello"

    def test_truncate_equal_to_max_length(self):
        """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
        assert truncate("hello", 5) == "hello"

    def test_truncate_longer_than_max_length(self):
        """Verifies text longer than max_length is truncated and ellipsis appended."""
        assert truncate("hello world", 5) == "hello..."

    def test_truncate_empty_string(self):
        """Verifies an empty string with a positive max_length returns empty string unchanged."""
        assert truncate("", 5) == ""

    @pytest.mark.parametrize("max_length", [0, -1, -100])
    def test_truncate_non_positive_max_length_raises_value_error(self, max_length):
        """Verifies non-positive max_length values are safely rejected with ValueError."""
        with pytest.raises(ValueError):
            truncate("hello world", max_length)

    def test_truncate_max_length_one(self):
        """Verifies truncation to a length of one character works with ellipsis appended."""
        assert truncate("hello", 1) == "h..."

    def test_truncate_with_injection_like_payload(self):
        """Verifies truncation safely handles injection-like payloads as inert text data."""
        payload = "<script>alert('xss')</script>"
        result = truncate(payload, 8)
        assert result == payload[:8] + "..."
        assert len(result) == 8 + 3

    def test_truncate_with_path_traversal_like_payload(self):
        """Verifies truncation safely handles path traversal-like strings as inert text data."""
        payload = "../../../../etc/passwd"
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."

    def test_truncate_non_integer_max_length_raises_type_error(self):
        """Verifies passing a non-integer, non-comparable max_length raises a TypeError instead of silently succeeding."""
        with pytest.raises(TypeError):
            truncate("hello", "5")

    def test_truncate_large_max_length_no_truncation(self):
        """Verifies a very large max_length results in the original text being returned unchanged."""
        text = "short text"
        assert truncate(text, 1_000_000) == text
