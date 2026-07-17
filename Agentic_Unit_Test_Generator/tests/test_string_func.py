import inspect

import pytest

import Agentic_Unit_Test_Generator.tests.test_string_func as tsf


# ---------- Structural checks on the module itself ----------

def test_module_exposes_reverse_string_capitalize_words_truncate():
    """Confirms reverse_string, capitalize_words, and truncate are present and callable on the module."""
    assert callable(tsf.reverse_string)
    assert callable(tsf.capitalize_words)
    assert callable(tsf.truncate)


def test_module_import_check_function_executes_cleanly():
    """The module's own import-structure self-check runs to completion and returns None."""
    result = tsf.test_module_imports_reverse_string_capitalize_words_truncate()
    assert result is None


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
def test_each_named_underlying_test_function_is_present_and_runs(func_name):
    """Each individual underlying unit test function exists as a callable attribute and executes without raising."""
    func = getattr(tsf, func_name, None)
    assert func is not None
    assert callable(func)
    func()  # should not raise


def test_structural_check_function_raises_on_missing_name():
    """The structural existence-check helper raises AssertionError when asked about a function that does not exist."""
    with pytest.raises(AssertionError):
        tsf.test_module_test_function_exists_and_is_callable("definitely_not_a_real_function_xyz")


def test_structural_check_function_passes_on_existing_name():
    """The structural existence-check helper returns None for a function name that genuinely exists on the module."""
    result = tsf.test_module_test_function_exists_and_is_callable("test_reverse_string_basic")
    assert result is None


# ---------- reverse_string functional and security behavior ----------

def test_reverse_string_reverses_basic_word():
    """reverse_string reverses a simple alphabetic word correctly."""
    assert tsf.reverse_string("hello") == "olleh"


def test_reverse_string_empty_string_returns_empty():
    """reverse_string returns an empty string when given an empty string."""
    assert tsf.reverse_string("") == ""


def test_reverse_string_single_character_returns_same_character():
    """reverse_string returns the same single character for a one-character input."""
    assert tsf.reverse_string("x") == "x"


def test_reverse_string_palindrome_returns_identical_string():
    """reverse_string returns an identical string for a palindrome input."""
    assert tsf.reverse_string("racecar") == "racecar"


def test_reverse_string_preserves_spaces_and_punctuation_order_reversed():
    """reverse_string correctly reverses a string containing spaces and punctuation."""
    assert tsf.reverse_string("Hi, there!") == "!ereht ,iH"


def test_reverse_string_handles_unicode_characters_correctly():
    """reverse_string correctly reverses a string containing non-ASCII unicode characters."""
    assert tsf.reverse_string("héllo") == "olléh"


def test_reverse_string_script_injection_payload_is_only_reversed_text():
    """A script-injection payload passed to reverse_string is only reversed as plain text, not executed or left intact as an active tag."""
    payload = "<script>alert(1)</script>"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert "<script>" not in result


def test_reverse_string_null_byte_embedded_is_handled_as_plain_data():
    """reverse_string treats an embedded null byte as ordinary character data without raising or corrupting output."""
    payload = "abc\x00xyz"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert isinstance(result, str)


def test_reverse_string_non_string_integer_raises_type_error():
    """reverse_string raises TypeError when given an integer instead of a string."""
    with pytest.raises(TypeError):
        tsf.reverse_string(12345)


def test_reverse_string_non_string_list_raises_type_error():
    """reverse_string raises TypeError when given a list, guarding against type-confusion input."""
    with pytest.raises(TypeError):
        tsf.reverse_string(["a", "b"])


def test_reverse_string_none_raises_type_error():
    """reverse_string raises TypeError when given None instead of a string."""
    with pytest.raises(TypeError):
        tsf.reverse_string(None)


def test_reverse_string_large_input_reverses_correctly_without_error():
    """reverse_string correctly reverses a large input string without truncation or resource errors."""
    payload = "a" * 5000 + "z"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert len(result) == len(payload)


# ---------- capitalize_words functional and security behavior ----------

def test_capitalize_words_capitalizes_each_word():
    """capitalize_words capitalizes the first letter of each space-separated word."""
    assert tsf.capitalize_words("foo bar") == "Foo Bar"


def test_capitalize_words_empty_string_returns_empty_string():
    """capitalize_words returns an empty string when given an empty string."""
    assert tsf.capitalize_words("") == ""


def test_capitalize_words_single_word_is_capitalized():
    """capitalize_words correctly capitalizes a single-word input."""
    assert tsf.capitalize_words("python") == "Python"


def test_capitalize_words_multiple_internal_spaces_collapsed_to_single():
    """capitalize_words collapses multiple internal spaces between words into a single space."""
    assert tsf.capitalize_words("foo    bar") == "Foo Bar"


def test_capitalize_words_strips_leading_and_trailing_whitespace():
    """capitalize_words strips leading and trailing whitespace from the result."""
    assert tsf.capitalize_words("   foo bar   ") == "Foo Bar"


def test_capitalize_words_already_uppercase_input_normalized():
    """capitalize_words normalizes an already-uppercase word to capitalized form."""
    assert tsf.capitalize_words("FOO") == "Foo"


def test_capitalize_words_mixed_case_input_normalized():
    """capitalize_words normalizes mixed-case words to a consistent capitalized form."""
    assert tsf.capitalize_words("fOo bAr") == "Foo Bar"


def test_capitalize_words_none_input_returns_empty_string_gracefully():
    """capitalize_words gracefully returns an empty string when given None instead of raising."""
    assert tsf.capitalize_words(None) == ""


def test_capitalize_words_whitespace_only_input_returns_empty_string():
    """capitalize_words returns an empty string when given a string composed only of whitespace."""
    assert tsf.capitalize_words("\t\n  ") == ""


def test_capitalize_words_html_injection_payload_only_capitalized_as_text():
    """An HTML/JS injection payload passed to capitalize_words is only word-capitalized as plain text and never executed."""
    payload = "<img src=x onerror=alert(1)>"
    result = tsf.capitalize_words(payload)
    assert isinstance(result, str)
    assert result.startswith("<img")


def test_capitalize_words_sql_injection_like_payload_only_capitalized_as_text():
    """A SQL-injection-like payload passed to capitalize_words is only capitalized as plain text, never interpreted as SQL."""
    payload = "select * from users; drop table users"
    result = tsf.capitalize_words(payload)
    assert result == "Select * From Users; Drop Table Users"


def test_capitalize_words_non_string_float_raises_attribute_error():
    """capitalize_words raises AttributeError when given a float, since it is neither a string nor None."""
    with pytest.raises(AttributeError):
        tsf.capitalize_words(3.14)


def test_capitalize_words_non_string_list_raises_attribute_error():
    """capitalize_words raises AttributeError when given a list instead of a string or None."""
    with pytest.raises(AttributeError):
        tsf.capitalize_words(["hello", "world"])


# ---------- truncate functional and security behavior ----------

def test_truncate_text_shorter_than_max_length_returned_unchanged():
    """truncate returns the original text unchanged when it is shorter than max_length."""
    assert tsf.truncate("hey", 50) == "hey"


def test_truncate_text_equal_to_max_length_returned_unchanged():
    """truncate returns the original text unchanged when its length exactly equals max_length."""
    assert tsf.truncate("hello", 5) == "hello"


def test_truncate_text_longer_than_max_length_appends_ellipsis():
    """truncate cuts text longer than max_length and appends an ellipsis."""
    assert tsf.truncate("abcdefgh", 3) == "abc..."


def test_truncate_max_length_zero_raises_value_error():
    """truncate raises ValueError when max_length is zero, enforcing a strict positive boundary."""
    with pytest.raises(ValueError):
        tsf.truncate("abc", 0)


def test_truncate_negative_max_length_raises_value_error():
    """truncate raises ValueError when max_length is negative, rejecting invalid boundary input."""
    with pytest.raises(ValueError):
        tsf.truncate("abc", -1)


def test_truncate_empty_text_with_positive_max_length_returns_empty_string():
    """truncate returns an empty string when given empty text, regardless of a positive max_length."""
    assert tsf.truncate("", 10) == ""


def test_truncate_max_length_one_returns_single_char_plus_ellipsis():
    """truncate with max_length of one returns just the first character followed by an ellipsis for longer text."""
    assert tsf.truncate("hello", 1) == "h..."


def test_truncate_very_large_max_length_returns_text_unchanged():
    """truncate returns text unchanged when max_length vastly exceeds the text's length."""
    assert tsf.truncate("short", 100000) == "short"


def test_truncate_path_traversal_payload_only_truncated_not_resolved():
    """A path-traversal payload passed to truncate is only truncated as plain text and never resolved as a filesystem path."""
    payload = "../../../../secret.txt"
    result = tsf.truncate(payload, 6)
    assert result == "../../..."
    assert "secret.txt" not in result


def test_truncate_command_injection_like_payload_only_truncated_as_text():
    """A shell-command-injection-like payload passed to truncate is only truncated as plain text, never executed."""
    payload = "; rm -rf / #"
    result = tsf.truncate(payload, 4)
    assert result == "; rm..."
    assert "-rf / #" not in result


def test_truncate_boolean_true_treated_as_integer_one():
    """truncate treats a boolean True max_length as integer 1 due to Python's bool/int equivalence."""
    assert tsf.truncate("hello", True) == "h..."


def test_truncate_boolean_false_treated_as_integer_zero_raises_value_error():
    """truncate treats a boolean False max_length as integer 0, triggering the same ValueError as an explicit zero."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", False)


def test_truncate_float_max_length_produces_truncated_string():
    """truncate does not silently ignore a float max_length; it still produces a truncated result distinct from the original."""
    text = "hello world"
    result = tsf.truncate(text, 5.5)
    assert isinstance(result, str)
    assert result != text


def test_truncate_non_string_text_raises_type_error_or_attribute_error():
    """truncate raises an error (TypeError or AttributeError) when given non-string text, rejecting type-confused input."""
    with pytest.raises((TypeError, AttributeError)):
        tsf.truncate(12345, 3)


# ---------- Module-level security/static-analysis self checks ----------

def test_module_dangerous_calls_check_executes_and_source_is_clean():
    """The module's own dangerous-call static-analysis check runs cleanly, and independent inspection confirms no eval/exec/os.system/subprocess/__import__ usage."""
    result = tsf.test_module_source_contains_no_dangerous_calls()
    assert result is None
    source = inspect.getsource(tsf)
    for token in ["eval(", "exec(", "os.system(", "subprocess.", "__import__("]:
        assert token not in source


def test_module_expected_symbols_check_executes_and_symbols_are_safe():
    """The module's own expected-symbols check runs cleanly, and independently only the intended safe functions are exposed as callables."""
    result = tsf.test_module_only_imports_expected_symbols()
    assert result is None
    for name in ("reverse_string", "capitalize_words", "truncate"):
        assert hasattr(tsf, name)
        assert callable(getattr(tsf, name))


def test_module_source_contains_no_dangerous_tokens_independent_check():
    """Independent static inspection of the module's source text confirms no dangerous execution primitives are present anywhere."""
    source = inspect.getsource(tsf)
    dangerous_tokens = ["eval(", "exec(", "os.system(", "subprocess.", "__import__("]
    for token in dangerous_tokens:
        assert token not in source
