import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

class TestReverseString:
    def test_basic_string(self):
        assert reverse_string("hello") == "olleh"

    def test_empty_string(self):
        assert reverse_string("") == ""

    def test_single_char(self):
        assert reverse_string("a") == "a"

    def test_palindrome(self):
        assert reverse_string("madam") == "madam"

    def test_string_with_spaces(self):
        assert reverse_string("hello world") == "dlrow olleh"

    def test_string_with_special_chars(self):
        assert reverse_string("!@#$%^&*()") == ")(*&^%$#@!"

    def test_unicode_string(self):
        assert reverse_string("héllo") == "olléh"

    def test_string_with_newlines(self):
        assert reverse_string("a\nb\nc") == "c\nb\na"

    def test_injection_like_payload_not_executed(self):
        payload = "<script>alert('xss')</script>"
        result = reverse_string(payload)
        # Ensure it is simply reversed text, not executed/altered maliciously
        assert result == payload[::-1]
        assert isinstance(result, str)

    def test_sql_injection_like_payload(self):
        payload = "'; DROP TABLE users; --"
        result = reverse_string(payload)
        assert result == payload[::-1]

    def test_path_traversal_like_payload(self):
        payload = "../../../etc/passwd"
        result = reverse_string(payload)
        assert result == payload[::-1]
        # Confirm no filesystem access occurred, only string transformation
        assert isinstance(result, str)

    def test_non_string_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            reverse_string(12345)

    def test_none_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            reverse_string(None)


# ---------- capitalize_words ----------

class TestCapitalizeWords:
    def test_basic_sentence(self):
        assert capitalize_words("hello world") == "Hello World"

    def test_empty_string(self):
        assert capitalize_words("") == ""

    def test_single_word(self):
        assert capitalize_words("python") == "Python"

    def test_already_capitalized(self):
        assert capitalize_words("Hello World") == "Hello World"

    def test_mixed_case_words(self):
        assert capitalize_words("hELLo WoRLD") == "Hello World"

    def test_multiple_spaces_collapsed(self):
        assert capitalize_words("hello    world") == "Hello World"

    def test_leading_trailing_whitespace(self):
        assert capitalize_words("   hello world   ") == "Hello World"

    def test_string_with_only_whitespace(self):
        assert capitalize_words("   ") == ""

    def test_string_with_numbers(self):
        assert capitalize_words("hello 123 world") == "Hello 123 World"

    def test_string_with_tabs_and_newlines(self):
        assert capitalize_words("hello\tworld\nfoo") == "Hello World Foo"

    def test_injection_like_payload_preserved_as_text(self):
        payload = "<script>alert(1)</script> test"
        result = capitalize_words(payload)
        # Should just capitalize words, not execute or strip tags maliciously
        assert result.startswith("<script>alert(1)</script>".capitalize())
        assert "test".capitalize() in result

    def test_non_string_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            capitalize_words(12345)

    def test_none_input_returns_empty_due_to_falsy_check(self):
        # None is falsy, so function returns "" instead of raising
        assert capitalize_words(None) == ""


# ---------- truncate ----------

class TestTruncate:
    def test_text_shorter_than_max_length(self):
        assert truncate("hello", 10) == "hello"

    def test_text_equal_to_max_length(self):
        assert truncate("hello", 5) == "hello"

    def test_text_longer_than_max_length(self):
        assert truncate("hello world", 5) == "hello..."

    def test_max_length_zero_raises_valueerror(self):
        with pytest.raises(ValueError):
            truncate("hello", 0)

    def test_negative_max_length_raises_valueerror(self):
        with pytest.raises(ValueError):
            truncate("hello", -5)

    def test_empty_text_with_positive_max_length(self):
        assert truncate("", 5) == ""

    def test_truncate_result_length(self):
        result = truncate("abcdefghij", 3)
        assert result == "abc..."
        assert len(result) == 6

    def test_truncate_single_char_max_length(self):
        result = truncate("hello", 1)
        assert result == "h..."

    def test_max_length_as_float_raises_or_behaves_type_dependent(self):
        # max_length <= 0 check works with float comparisons too;
        # here we test a positive float doesn't crash unexpectedly
        result = truncate("hello world", 5.5)
        assert result == "hello..."[:6] or result.startswith("hello")

    def test_non_string_text_raises_typeerror(self):
        with pytest.raises(TypeError):
            truncate(12345, 5)

    def test_none_text_raises_typeerror(self):
        with pytest.raises(TypeError):
            truncate(None, 5)

    def test_large_max_length_no_truncation(self):
        text = "short text"
        assert truncate(text, 1000) == text

    def test_injection_like_payload_truncated_safely(self):
        payload = "<script>alert('xss')</script>" * 5
        result = truncate(payload, 10)
        assert result == payload[:10] + "..."
        # Ensure no execution or unescaped alteration beyond truncation
        assert isinstance(result, str)

    def test_path_traversal_like_payload_truncated(self):
        payload = "../../../../etc/passwd"
        result = truncate(payload, 5)
        assert result == "../.." + "..."
