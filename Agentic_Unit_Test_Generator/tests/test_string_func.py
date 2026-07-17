import pytest

from Agentic_Unit_Test_Generator.tests import test_string_func as source_module

reverse_string = source_module.reverse_string
capitalize_words = source_module.capitalize_words
truncate = source_module.truncate


# ---------- reverse_string ----------

def test_reverse_string_basic_direct():
    """Verifies a simple string is reversed correctly via direct function call."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty_direct():
    """Verifies an empty string reverses to an empty string via direct function call."""
    assert reverse_string("") == ""


def test_reverse_string_single_char_direct():
    """Verifies a single character string reverses to itself via direct function call."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome_direct():
    """Verifies a palindrome remains unchanged after reversal via direct function call."""
    assert reverse_string("madam") == "madam"


def test_reverse_string_with_spaces_and_punctuation_direct():
    """Verifies strings with spaces and punctuation are reversed correctly via direct function call."""
    assert reverse_string("Hello, World!") == "!dlroW ,olleH"


def test_reverse_string_unicode_direct():
    """Verifies unicode characters are reversed without corruption via direct function call."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_injection_payload_is_inert_direct():
    """Verifies a script injection payload is only reversed as plain text, not executed or altered."""
    payload = "<script>alert('xss')</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    assert "<script>" not in result
    assert isinstance(result, str)


def test_reverse_string_non_string_raises_type_error_direct():
    """Verifies passing a non-string type raises a TypeError due to unsupported slicing."""
    with pytest.raises(TypeError):
        reverse_string(12345)


def test_reverse_string_list_input_raises_type_error_direct():
    """Verifies passing a list input raises a TypeError, guarding against type confusion."""
    with pytest.raises(TypeError):
        reverse_string([1, 2, 3])


def test_reverse_string_double_reversal_restores_original_direct():
    """Verifies reversing a string twice restores the original value, confirming correctness invariant."""
    original = "SecurityTest123!"
    assert reverse_string(reverse_string(original)) == original


# ---------- capitalize_words ----------

def test_capitalize_words_basic_direct():
    """Verifies each word in a sentence is capitalized correctly via direct function call."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string_direct():
    """Verifies an empty string returns an empty string via direct function call."""
    assert capitalize_words("") == ""


def test_capitalize_words_already_capitalized_direct():
    """Verifies words that are already capitalized remain properly capitalized via direct function call."""
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_capitalize_words_single_word_direct():
    """Verifies a single word input is capitalized correctly via direct function call."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_multiple_spaces_collapsed_direct():
    """Verifies multiple spaces between words are collapsed by split()/join() via direct function call."""
    assert capitalize_words("hello   world") == "Hello World"


def test_capitalize_words_leading_trailing_whitespace_direct():
    """Verifies leading and trailing whitespace is stripped due to split() behavior via direct function call."""
    assert capitalize_words("  hello world  ") == "Hello World"


def test_capitalize_words_only_whitespace_direct():
    """Verifies a string of only whitespace returns an empty string via direct function call."""
    assert capitalize_words("   ") == ""


def test_capitalize_words_with_numbers_and_symbols_direct():
    """Verifies words containing numbers or symbols are still capitalized at the first character."""
    assert capitalize_words("123abc test-case") == "123abc Test-case"


def test_capitalize_words_none_input_returns_empty_direct():
    """Verifies that a falsy None input safely returns an empty string rather than crashing."""
    assert capitalize_words(None) == ""


def test_capitalize_words_injection_payload_capitalized_safely_direct():
    """Verifies an HTML injection-style payload is only text-processed, not executed, and result is plain text."""
    payload = "<img src=x onerror=alert(1)>"
    result = capitalize_words(payload)
    assert result == "<img Src=x Onerror=alert(1)>"
    assert isinstance(result, str)
    assert "<script>" not in result


def test_capitalize_words_non_string_non_none_raises_type_error_direct():
    """Verifies passing a non-string, non-None type (e.g. int) raises a TypeError due to unsupported split()."""
    with pytest.raises(TypeError):
        capitalize_words(12345)


# ---------- truncate ----------

def test_truncate_shorter_than_max_length_direct():
    """Verifies text shorter than max_length is returned unmodified via direct function call."""
    assert truncate("hello", 10) == "hello"


def test_truncate_equal_to_max_length_direct():
    """Verifies text exactly equal to max_length is returned unmodified without ellipses."""
    assert truncate("hello", 5) == "hello"


def test_truncate_longer_than_max_length_direct():
    """Verifies text longer than max_length is truncated and ellipses are appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises_value_error_direct():
    """Verifies a zero max_length raises a ValueError to prevent invalid truncation."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_value_error_direct():
    """Verifies a negative max_length raises a ValueError, guarding against invalid boundary input."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text_direct():
    """Verifies an empty text string with a valid max_length returns an empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one_direct():
    """Verifies truncation works correctly with the smallest valid positive max_length."""
    assert truncate("hello", 1) == "h..."


def test_truncate_non_integer_max_length_raises_type_error_direct():
    """Verifies passing a non-integer max_length (e.g. string) raises a TypeError on comparison."""
    with pytest.raises(TypeError):
        truncate("hello", "5")


def test_truncate_long_injection_payload_gets_safely_truncated_direct():
    """Verifies a long injection-style payload is truncated to the requested length plus ellipses, not executed."""
    payload = "<script>" + "A" * 100 + "</script>"
    result = truncate(payload, 8)
    assert result == "<script>..."
    assert len(result) == 8 + 3
    assert "AAAAAAAA" not in result


def test_truncate_path_traversal_string_truncated_as_plain_text_direct():
    """Verifies a path traversal-like string is treated as plain text and truncated safely without filesystem access."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 10)
    assert result == "../../../..."
    assert isinstance(result, str)
    assert "/etc/passwd" not in result


def test_truncate_none_text_raises_type_error_direct():
    """Verifies passing None as text raises a TypeError due to unsupported len()/slicing on NoneType."""
    with pytest.raises(TypeError):
        truncate(None, 5)


def test_truncate_boolean_max_length_behaves_as_integer_direct():
    """Verifies that a boolean max_length (subclass of int) is handled per Python's int semantics without crashing."""
    result = truncate("hello", True)
    assert result == "h..."


# ---------- module structure sanity checks ----------

def test_source_module_exposes_expected_test_functions():
    """Verifies the source test module defines all expected test functions as callables for functionality and security coverage."""
    expected_names = [
        "test_reverse_string_basic",
        "test_reverse_string_empty",
        "test_reverse_string_single_char",
        "test_reverse_string_palindrome",
        "test_reverse_string_with_spaces_and_punctuation",
        "test_reverse_string_unicode",
        "test_reverse_string_injection_payload_is_inert",
        "test_reverse_string_non_string_raises_type_error",
        "test_capitalize_words_basic",
        "test_capitalize_words_empty_string",
        "test_capitalize_words_already_capitalized",
        "test_capitalize_words_single_word",
        "test_capitalize_words_multiple_spaces_collapsed",
        "test_capitalize_words_leading_trailing_whitespace",
        "test_capitalize_words_only_whitespace",
        "test_capitalize_words_with_numbers_and_symbols",
        "test_capitalize_words_none_input_returns_empty",
        "test_capitalize_words_injection_payload_capitalized_safely",
        "test_truncate_shorter_than_max_length",
        "test_truncate_equal_to_max_length",
        "test_truncate_longer_than_max_length",
        "test_truncate_zero_max_length_raises_value_error",
        "test_truncate_negative_max_length_raises_value_error",
        "test_truncate_empty_text",
        "test_truncate_max_length_one",
        "test_truncate_non_integer_max_length_raises_type_error",
        "test_truncate_long_injection_payload_gets_safely_truncated",
        "test_truncate_path_traversal_string_truncated_as_plain_text",
    ]
    missing = [name for name in expected_names if not hasattr(source_module, name)]
    assert missing == [], f"Missing expected test function(s): {missing}"
    non_callables = [
        name for name in expected_names if not callable(getattr(source_module, name))
    ]
    assert non_callables == [], f"Expected callable test function(s): {non_callables}"


def test_source_module_imports_expected_target_functions():
    """Verifies the source test module correctly imports reverse_string, capitalize_words, and truncate for testing."""
    assert callable(source_module.reverse_string)
    assert callable(source_module.capitalize_words)
    assert callable(source_module.truncate)
    assert source_module.reverse_string("abc") == "cba"
    assert source_module.capitalize_words("abc def") == "Abc Def"
    assert source_module.truncate("abcdef", 3) == "abc..."
