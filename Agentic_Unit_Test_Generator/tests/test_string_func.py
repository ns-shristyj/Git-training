import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


class TestReverseString:
    def test_simple_string(self):
        assert reverse_string("hello") == "olleh"

    def test_empty_string(self):
        assert reverse_string("") == ""

    def test_single_character(self):
        assert reverse_string("a") == "a"

    def test_palindrome(self):
        assert reverse_string("racecar") == "racecar"

    def test_string_with_spaces(self):
        assert reverse_string("hello world") == "dlrow olleh"

    def test_string_with_special_chars(self):
        assert reverse_string("a!b@c#") == "#c@b!a"

    def test_unicode_string(self):
        assert reverse_string("héllo") == "olléh"

    def test_numeric_string(self):
        assert reverse_string("12345") == "54321"

    def test_non_string_input_raises_type_error(self):
        with pytest.raises(TypeError):
            reverse_string(12345)


class TestCapitalizeWords:
    def test_empty_string_returns_empty(self):
        assert capitalize_words("") == ""

    def test_single_word(self):
        assert capitalize_words("hello") == "Hello"

    def test_multiple_words(self):
        assert capitalize_words("hello world") == "Hello World"

    def test_already_capitalized(self):
        assert capitalize_words("Hello World") == "Hello World"

    def test_all_caps_words_lowercased_except_first(self):
        assert capitalize_words("HELLO WORLD") == "Hello World"

    def test_mixed_case_words(self):
        assert capitalize_words("hELLO wORLD") == "Hello World"

    def test_extra_whitespace_collapsed(self):
        assert capitalize_words("  hello   world  ") == "Hello World"

    def test_none_input_returns_empty_string(self):
        # `if not text` triggers on None, returning ""
        assert capitalize_words(None) == ""

    def test_whitespace_only_string(self):
        assert capitalize_words("   ") == ""

    def test_single_letter_words(self):
        assert capitalize_words("a b c") == "A B C"

    def test_words_with_numbers(self):
        assert capitalize_words("hello123 world456") == "Hello123 World456"

    def test_non_string_non_none_raises_error(self):
        with pytest.raises(AttributeError):
            capitalize_words(12345)


class TestTruncate:
    def test_text_shorter_than_max_length(self):
        assert truncate("hello", 10) == "hello"

    def test_text_equal_to_max_length(self):
        assert truncate("hello", 5) == "hello"

    def test_text_longer_than_max_length(self):
        assert truncate("hello world", 5) == "hello..."

    def test_max_length_one(self):
        assert truncate("hello", 1) == "h..."

    def test_max_length_zero_raises_value_error(self):
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_negative_max_length_raises_value_error(self):
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_empty_text_with_positive_max_length(self):
        assert truncate("", 5) == ""

    def test_truncate_exact_boundary_minus_one(self):
        assert truncate("hello", 4) == "hell..."

    def test_truncate_long_text(self):
        text = "a" * 1000
        result = truncate(text, 100)
        assert result == "a" * 100 + "..."
        assert len(result) == 103

    def test_non_string_text_raises_type_error(self):
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_non_integer_max_length_raises_type_error(self):
        with pytest.raises(TypeError):
            truncate("hello", "5")
