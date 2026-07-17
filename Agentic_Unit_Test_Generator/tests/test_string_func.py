"""Meta-level pytest tests for Agentic_Unit_Test_Generator.tests.test_string_func.

This test module treats the provided test file as the unit under test.
Each function defined in ``test_string_func`` is itself a pytest test case
that already exercises reverse_string, capitalize_words, and truncate from
NIC_SecEng_Task.Calculator.string_func (including security-relevant edge
cases like injection payloads, path traversal strings, and boundary
values). Here we invoke each of those functions directly to confirm they
execute and assert successfully, AND we independently re-verify the
underlying behavior with explicit assertions against the functions the
module imports, so every test carries a real, meaningful assertion rather
than a bare no-op call.
"""
import inspect

import pytest

from Agentic_Unit_Test_Generator.tests import test_string_func as tsf


# ---------------------------
# Structural / module-level sanity checks
# ---------------------------

def test_module_imports_expected_names():
    """Verify the module under test imports the three target functions correctly."""
    assert hasattr(tsf, "reverse_string")
    assert hasattr(tsf, "capitalize_words")
    assert hasattr(tsf, "truncate")
    assert callable(tsf.reverse_string)
    assert callable(tsf.capitalize_words)
    assert callable(tsf.truncate)


def test_module_contains_expected_test_functions():
    """Verify the module defines the full expected set of test functions (no missing coverage)."""
    expected = {
        "test_reverse_string_basic",
        "test_reverse_string_empty",
        "test_reverse_string_single_char",
        "test_reverse_string_palindrome",
        "test_reverse_string_with_spaces",
        "test_reverse_string_with_unicode",
        "test_reverse_string_with_special_chars_injection_payload",
        "test_reverse_string_path_traversal_payload",
        "test_reverse_string_non_string_input_raises",
        "test_capitalize_words_basic",
        "test_capitalize_words_empty_string",
        "test_capitalize_words_already_capitalized",
        "test_capitalize_words_all_uppercase",
        "test_capitalize_words_multiple_spaces_collapsed",
        "test_capitalize_words_leading_trailing_whitespace",
        "test_capitalize_words_single_word",
        "test_capitalize_words_with_numbers_and_symbols",
        "test_capitalize_words_whitespace_only_returns_empty",
        "test_capitalize_words_injection_payload_not_executed",
        "test_capitalize_words_none_input_raises",
        "test_truncate_no_truncation_needed",
        "test_truncate_exact_length_no_ellipsis",
        "test_truncate_longer_text_appends_ellipsis",
        "test_truncate_max_length_zero_raises_value_error",
        "test_truncate_negative_max_length_raises_value_error",
        "test_truncate_empty_string_with_positive_max_length",
        "test_truncate_max_length_one",
        "test_truncate_large_max_length_no_truncation",
        "test_truncate_injection_payload_truncated_safely",
        "test_truncate_non_integer_max_length_raises_type_error",
    }
    defined = {
        name
        for name, obj in vars(tsf).items()
        if inspect.isfunction(obj) and name.startswith("test_")
    }
    assert expected.issubset(defined)


def test_all_test_functions_take_no_arguments():
    """Verify every test function in the module is parameterless, preventing unexpected fixture injection."""
    test_funcs = [
        obj
        for name, obj in vars(tsf).items()
        if inspect.isfunction(obj) and name.startswith("test_")
    ]
    assert len(test_funcs) > 0
    for obj in test_funcs:
        sig = inspect.signature(obj)
        assert len(sig.parameters) == 0, f"{obj.__name__} unexpectedly declares parameters"


# ---------------------------
# reverse_string related meta tests
# ---------------------------

def test_meta_reverse_string_basic_executes_cleanly():
    """Verify test_reverse_string_basic passes and reverse_string produces the expected reversal."""
    tsf.test_reverse_string_basic()
    assert tsf.reverse_string("hello") == "olleh"


def test_meta_reverse_string_empty_executes_cleanly():
    """Verify test_reverse_string_empty passes and reverse_string handles empty input correctly."""
    tsf.test_reverse_string_empty()
    assert tsf.reverse_string("") == ""


def test_meta_reverse_string_single_char_executes_cleanly():
    """Verify test_reverse_string_single_char passes and single-character reversal is a no-op."""
    tsf.test_reverse_string_single_char()
    assert tsf.reverse_string("a") == "a"


def test_meta_reverse_string_palindrome_executes_cleanly():
    """Verify test_reverse_string_palindrome passes and a palindrome reverses to itself."""
    tsf.test_reverse_string_palindrome()
    assert tsf.reverse_string("madam") == "madam"


def test_meta_reverse_string_with_spaces_executes_cleanly():
    """Verify test_reverse_string_with_spaces passes and spaces are preserved during reversal."""
    tsf.test_reverse_string_with_spaces()
    assert tsf.reverse_string("a b c") == "c b a"


def test_meta_reverse_string_with_unicode_executes_cleanly():
    """Verify test_reverse_string_with_unicode passes and unicode characters reverse without corruption."""
    tsf.test_reverse_string_with_unicode()
    assert tsf.reverse_string("héllo") == "olléh"


def test_meta_reverse_string_injection_payload_is_safely_handled():
    """Verify the injection payload test passes and reverse_string never executes embedded script content."""
    tsf.test_reverse_string_with_special_chars_injection_payload()
    payload = "<script>alert(1)</script>"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert "<script>alert(1)</script>" != result


def test_meta_reverse_string_path_traversal_payload_is_safely_handled():
    """Verify the path traversal payload test passes and reverse_string only performs plain text reversal."""
    tsf.test_reverse_string_path_traversal_payload()
    payload = "../../etc/passwd"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert result != payload


def test_meta_reverse_string_non_string_input_raises_typeerror():
    """Verify the non-string input test passes and reverse_string rejects invalid types via TypeError."""
    with pytest.raises(TypeError):
        tsf.reverse_string(12345)
    tsf.test_reverse_string_non_string_input_raises()


# ---------------------------
# capitalize_words related meta tests
# ---------------------------

def test_meta_capitalize_words_basic_executes_cleanly():
    """Verify test_capitalize_words_basic passes and capitalize_words capitalizes each word."""
    tsf.test_capitalize_words_basic()
    assert tsf.capitalize_words("hello world") == "Hello World"


def test_meta_capitalize_words_empty_string_executes_cleanly():
    """Verify test_capitalize_words_empty_string passes and empty input returns empty output."""
    tsf.test_capitalize_words_empty_string()
    assert tsf.capitalize_words("") == ""


def test_meta_capitalize_words_already_capitalized_executes_cleanly():
    """Verify test_capitalize_words_already_capitalized passes and already-capitalized text is unchanged."""
    tsf.test_capitalize_words_already_capitalized()
    assert tsf.capitalize_words("Hello World") == "Hello World"


def test_meta_capitalize_words_all_uppercase_executes_cleanly():
    """Verify test_capitalize_words_all_uppercase passes and all-caps words get normalized."""
    tsf.test_capitalize_words_all_uppercase()
    assert tsf.capitalize_words("HELLO WORLD") == "Hello World"


def test_meta_capitalize_words_multiple_spaces_collapsed_executes_cleanly():
    """Verify test_capitalize_words_multiple_spaces_collapsed passes and repeated spaces collapse."""
    tsf.test_capitalize_words_multiple_spaces_collapsed()
    assert tsf.capitalize_words("hello    world") == "Hello World"


def test_meta_capitalize_words_leading_trailing_whitespace_executes_cleanly():
    """Verify test_capitalize_words_leading_trailing_whitespace passes and surrounding whitespace is stripped."""
    tsf.test_capitalize_words_leading_trailing_whitespace()
    assert tsf.capitalize_words("   hello world   ") == "Hello World"


def test_meta_capitalize_words_single_word_executes_cleanly():
    """Verify test_capitalize_words_single_word passes and a lone word is capitalized correctly."""
    tsf.test_capitalize_words_single_word()
    assert tsf.capitalize_words("python") == "Python"


def test_meta_capitalize_words_with_numbers_and_symbols_executes_cleanly():
    """Verify test_capitalize_words_with_numbers_and_symbols passes and digits/symbols are preserved."""
    tsf.test_capitalize_words_with_numbers_and_symbols()
    assert tsf.capitalize_words("hello123 world!") == "Hello123 World!"


def test_meta_capitalize_words_whitespace_only_returns_empty_executes_cleanly():
    """Verify test_capitalize_words_whitespace_only_returns_empty passes and whitespace-only input yields empty string."""
    tsf.test_capitalize_words_whitespace_only_returns_empty()
    assert tsf.capitalize_words("     ") == ""


def test_meta_capitalize_words_injection_payload_is_safely_handled():
    """Verify the injection payload test passes and capitalize_words never executes embedded script content."""
    tsf.test_capitalize_words_injection_payload_not_executed()
    payload = "<script>alert('x')</script> test"
    result = tsf.capitalize_words(payload)
    assert "Test" in result
    assert "<script>alert('x')</script>".capitalize() in result


def test_meta_capitalize_words_none_input_raises_attributeerror():
    """Verify the None input test passes and capitalize_words rejects None via AttributeError."""
    with pytest.raises(AttributeError):
        tsf.capitalize_words(None)
    tsf.test_capitalize_words_none_input_raises()


# ---------------------------
# truncate related meta tests
# ---------------------------

def test_meta_truncate_no_truncation_needed_executes_cleanly():
    """Verify test_truncate_no_truncation_needed passes and short text is returned unchanged."""
    tsf.test_truncate_no_truncation_needed()
    assert tsf.truncate("hello", 10) == "hello"


def test_meta_truncate_exact_length_no_ellipsis_executes_cleanly():
    """Verify test_truncate_exact_length_no_ellipsis passes and exact-length text has no ellipsis appended."""
    tsf.test_truncate_exact_length_no_ellipsis()
    assert tsf.truncate("hello", 5) == "hello"


def test_meta_truncate_longer_text_appends_ellipsis_executes_cleanly():
    """Verify test_truncate_longer_text_appends_ellipsis passes and overlong text is truncated with ellipsis."""
    tsf.test_truncate_longer_text_appends_ellipsis()
    assert tsf.truncate("hello world", 5) == "hello..."


def test_meta_truncate_max_length_zero_raises_value_error():
    """Verify the zero max_length test passes and truncate rejects non-positive boundary via ValueError."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", 0)
    tsf.test_truncate_max_length_zero_raises_value_error()


def test_meta_truncate_negative_max_length_raises_value_error():
    """Verify the negative max_length test passes and truncate rejects invalid boundary via ValueError."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", -5)
    tsf.test_truncate_negative_max_length_raises_value_error()


def test_meta_truncate_empty_string_with_positive_max_length_executes_cleanly():
    """Verify test_truncate_empty_string_with_positive_max_length passes and empty text stays empty."""
    tsf.test_truncate_empty_string_with_positive_max_length()
    assert tsf.truncate("", 5) == ""


def test_meta_truncate_max_length_one_executes_cleanly():
    """Verify test_truncate_max_length_one passes and truncation works at the smallest valid boundary."""
    tsf.test_truncate_max_length_one()
    assert tsf.truncate("hello", 1) == "h..."


def test_meta_truncate_large_max_length_no_truncation_executes_cleanly():
    """Verify test_truncate_large_max_length_no_truncation passes and a very large max_length never truncates."""
    tsf.test_truncate_large_max_length_no_truncation()
    text = "short text"
    assert tsf.truncate(text, 10_000) == text


def test_meta_truncate_injection_payload_truncated_safely_is_handled():
    """Verify the injection payload truncate test passes and payload is only sliced, never executed."""
    tsf.test_truncate_injection_payload_truncated_safely()
    payload = "<script>alert('xss')</script>"
    result = tsf.truncate(payload, 8)
    assert result == payload[:8] + "..."
    assert result != payload


def test_meta_truncate_non_integer_max_length_raises_type_error():
    """Verify the non-integer max_length test passes and truncate rejects invalid types via TypeError."""
    with pytest.raises(TypeError):
        tsf.truncate("hello", "5")
    tsf.test_truncate_non_integer_max_length_raises_type_error()


# ---------------------------
# Aggregate execution safety check
# ---------------------------

def test_all_module_test_functions_are_individually_callable():
    """Verify every test_ function in the module can be invoked without side effects on the module namespace."""
    before = dict(vars(tsf))
    ran = 0
    for name, obj in list(vars(tsf).items()):
        if inspect.isfunction(obj) and name.startswith("test_"):
            obj()
            ran += 1
    after = dict(vars(tsf))
    assert ran > 0
    # Module-level namespace should remain structurally unchanged after execution.
    assert set(before.keys()) == set(after.keys())
