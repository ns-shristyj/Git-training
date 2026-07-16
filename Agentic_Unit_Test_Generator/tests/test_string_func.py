import inspect

import pytest

import Agentic_Unit_Test_Generator.tests.test_string_func as tsf


# ---------- Structural checks: ensure expected functions/imports exist ----------

def test_module_imports_reverse_string_capitalize_words_truncate():
    """The module correctly imports reverse_string, capitalize_words, and truncate as callables."""
    assert callable(tsf.reverse_string)
    assert callable(tsf.capitalize_words)
    assert callable(tsf.truncate)


@pytest.mark.parametrize(
    "func_name",
    [
        "test_reverse_string_basic",
        "test_reverse_string_empty",
        "test_reverse_string_single_char",
        "test_reverse_string_palindrome",
        "test_reverse_string_with_spaces_and_punctuation",
        "test_reverse_string_unicode",
        "test_reverse_string_injection_payload_safe",
        "test_reverse_string_non_string_raises_type_error",
        "test_capitalize_words_basic",
        "test_capitalize_words_empty_string",
        "test_capitalize_words_single_word",
        "test_capitalize_words_multiple_spaces_collapsed",
        "test_capitalize_words_leading_trailing_whitespace",
        "test_capitalize_words_already_uppercase",
        "test_capitalize_words_mixed_case",
        "test_capitalize_words_none_returns_empty_string",
        "test_capitalize_words_only_whitespace",
        "test_capitalize_words_injection_payload_preserved_not_executed",
        "test_capitalize_words_non_string_raises_attribute_error",
        "test_truncate_text_shorter_than_max_length",
        "test_truncate_text_equal_to_max_length",
        "test_truncate_text_longer_than_max_length",
        "test_truncate_max_length_zero_raises_value_error",
        "test_truncate_negative_max_length_raises_value_error",
        "test_truncate_empty_text_with_positive_max_length",
        "test_truncate_max_length_one",
        "test_truncate_very_large_max_length",
        "test_truncate_path_traversal_payload_only_truncated_not_resolved",
    ],
)
def test_module_test_function_exists_and_is_callable(func_name):
    """Each expected test function is present on the module and is callable, confirming module structure integrity."""
    func = getattr(tsf, func_name, None)
    assert func is not None, f"{func_name} is missing from the module"
    assert callable(func)


# ---------- Direct functional re-verification via the module's imported symbols ----------

def test_module_reverse_string_basic_via_module_namespace():
    """reverse_string accessed through the module namespace reverses a basic ASCII string correctly."""
    assert tsf.reverse_string("hello") == "olleh"


def test_module_reverse_string_empty_via_module_namespace():
    """reverse_string accessed through the module namespace returns empty string for empty input."""
    assert tsf.reverse_string("") == ""


def test_module_reverse_string_unicode_via_module_namespace():
    """reverse_string accessed through the module namespace correctly reverses unicode characters without corruption."""
    assert tsf.reverse_string("héllo") == "olléh"


def test_module_reverse_string_injection_payload_not_executed_via_module():
    """An injection-like payload passed to reverse_string via the module is only reversed as text, never executed."""
    payload = "<script>alert(1)</script>"
    result = tsf.reverse_string(payload)
    assert isinstance(result, str)
    assert result == payload[::-1]
    assert result != payload


def test_module_reverse_string_non_string_raises_type_error_via_module():
    """Calling reverse_string with a non-string type through the module raises TypeError, confirming type validation boundary."""
    with pytest.raises(TypeError):
        tsf.reverse_string(12345)


def test_module_capitalize_words_basic_via_module_namespace():
    """capitalize_words accessed through the module namespace capitalizes each word in a normal sentence."""
    assert tsf.capitalize_words("hello world") == "Hello World"


def test_module_capitalize_words_multiple_spaces_collapsed_via_module():
    """capitalize_words accessed through the module namespace collapses multiple spaces between words."""
    assert tsf.capitalize_words("hello   world") == "Hello World"


def test_module_capitalize_words_none_input_does_not_crash_via_module():
    """Calling capitalize_words with None through the module returns an empty string rather than raising."""
    assert tsf.capitalize_words(None) == ""


def test_module_capitalize_words_only_whitespace_via_module():
    """capitalize_words accessed through the module namespace returns an empty string for whitespace-only input."""
    assert tsf.capitalize_words("   ") == ""


def test_module_capitalize_words_injection_payload_not_executed_via_module():
    """An injection-like payload passed to capitalize_words via the module is only word-capitalized text, never executed."""
    payload = "<script>alert('x')</script> attack"
    result = tsf.capitalize_words(payload)
    assert isinstance(result, str)
    assert result == "<script>alert('x')</script> Attack"


def test_module_capitalize_words_non_string_raises_attribute_error_via_module():
    """Calling capitalize_words with a non-string, non-None type through the module raises AttributeError."""
    with pytest.raises(AttributeError):
        tsf.capitalize_words(12345)


def test_module_truncate_text_shorter_than_max_length_via_module():
    """truncate accessed through the module namespace returns short text unchanged."""
    assert tsf.truncate("hi", 10) == "hi"


def test_module_truncate_text_longer_than_max_length_via_module():
    """truncate accessed through the module namespace truncates and appends ellipsis for long text."""
    assert tsf.truncate("hello world", 5) == "hello..."


def test_module_truncate_max_length_zero_raises_value_error_via_module():
    """Calling truncate with max_length of zero through the module raises ValueError, confirming boundary validation."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", 0)


def test_module_truncate_negative_max_length_raises_value_error_via_module():
    """Calling truncate with a negative max_length through the module raises ValueError, confirming boundary validation."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", -5)


def test_module_truncate_path_traversal_payload_not_resolved_via_module():
    """A path traversal-like payload passed to truncate via the module is only truncated as text, never resolved as a filesystem path."""
    payload = "../../../../etc/passwd"
    result = tsf.truncate(payload, 5)
    assert isinstance(result, str)
    assert result == "../..."
    assert "/etc/passwd" not in result


# ---------- Security/static-analysis style checks on this test module's own source ----------

def test_module_source_contains_no_dangerous_calls():
    """The test module's source code must not contain calls to eval, exec, os.system, or subprocess, guarding against injected code execution."""
    source = inspect.getsource(tsf)
    dangerous_tokens = ["eval(", "exec(", "os.system(", "subprocess.", "__import__("]
    for token in dangerous_tokens:
        assert token not in source, f"Dangerous call pattern found in module source: {token}"


def test_module_only_imports_expected_symbols():
    """The module's public functions imported from string_func are limited to the expected safe set, preventing unexpected symbol exposure."""
    expected_imports = {"reverse_string", "capitalize_words", "truncate"}
    for name in expected_imports:
        assert hasattr(tsf, name)
        assert callable(getattr(tsf, name))
