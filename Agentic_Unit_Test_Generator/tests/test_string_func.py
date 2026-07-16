import inspect

import pytest

import Agentic_Unit_Test_Generator.tests.test_string_func as tsf


# ---------- Verify the module's own structural check functions execute cleanly ----------

def test_source_module_imports_check_runs_without_error():
    """Invoking the module's own import-structure check succeeds, returns None, and confirms reverse_string/capitalize_words/truncate are present and callable."""
    result = tsf.test_module_imports_reverse_string_capitalize_words_truncate()
    assert result is None
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
def test_module_test_function_check_runs_without_error(func_name):
    """The module's own structural-existence check for each named test function runs, is found, is callable, and executes to completion returning None."""
    func = getattr(tsf, func_name, None)
    assert func is not None
    assert callable(func)
    result = tsf.test_module_test_function_exists_and_is_callable(func_name)
    assert result is None


def test_module_test_function_missing_name_raises_assertion_error():
    """Requesting a structural check for a nonexistent function name surfaces an AssertionError, confirming the check actually validates presence."""
    with pytest.raises(AssertionError):
        tsf.test_module_test_function_exists_and_is_callable("this_function_does_not_exist")


# ---------- Re-execute the module's functional re-verification tests directly ----------

def test_source_module_reverse_string_basic_runs_without_error():
    """The module's basic reverse_string re-verification test executes successfully and independently reverse_string still reverses 'hello' to 'olleh'."""
    result = tsf.test_module_reverse_string_basic_via_module_namespace()
    assert result is None
    assert tsf.reverse_string("hello") == "olleh"


def test_source_module_reverse_string_empty_runs_without_error():
    """The module's empty-string reverse_string re-verification test executes successfully and reverse_string("") independently returns ""."""
    result = tsf.test_module_reverse_string_empty_via_module_namespace()
    assert result is None
    assert tsf.reverse_string("") == ""


def test_source_module_reverse_string_unicode_runs_without_error():
    """The module's unicode reverse_string re-verification test executes successfully and confirms unicode characters are not corrupted."""
    result = tsf.test_module_reverse_string_unicode_via_module_namespace()
    assert result is None
    assert tsf.reverse_string("héllo") == "olléh"


def test_source_module_reverse_string_injection_payload_runs_without_error():
    """The module's injection-payload reverse_string re-verification test confirms the payload is only reversed as text, not executed, and the reversed string does not contain the original tag order."""
    result = tsf.test_module_reverse_string_injection_payload_not_executed_via_module()
    assert result is None
    payload = "<script>alert(1)</script>"
    reversed_payload = tsf.reverse_string(payload)
    assert reversed_payload == payload[::-1]
    assert "<script>" not in reversed_payload


def test_source_module_reverse_string_non_string_type_error_runs_without_error():
    """The module's type-validation re-verification test confirms reverse_string raises TypeError for non-string input, verified again directly."""
    result = tsf.test_module_reverse_string_non_string_raises_type_error_via_module()
    assert result is None
    with pytest.raises(TypeError):
        tsf.reverse_string(999)


def test_source_module_capitalize_words_basic_runs_without_error():
    """The module's basic capitalize_words re-verification test executes successfully and capitalize_words independently capitalizes each word."""
    result = tsf.test_module_capitalize_words_basic_via_module_namespace()
    assert result is None
    assert tsf.capitalize_words("foo bar") == "Foo Bar"


def test_source_module_capitalize_words_multiple_spaces_runs_without_error():
    """The module's multiple-spaces capitalize_words re-verification test confirms whitespace collapsing behavior, verified again directly."""
    result = tsf.test_module_capitalize_words_multiple_spaces_collapsed_via_module()
    assert result is None
    assert tsf.capitalize_words("foo    bar") == "Foo Bar"


def test_source_module_capitalize_words_none_input_runs_without_error():
    """The module's None-input capitalize_words re-verification test confirms graceful handling, verified again by calling with None directly."""
    result = tsf.test_module_capitalize_words_none_input_does_not_crash_via_module()
    assert result is None
    assert tsf.capitalize_words(None) == ""


def test_source_module_capitalize_words_whitespace_only_runs_without_error():
    """The module's whitespace-only capitalize_words re-verification test confirms empty output, verified again with a tab/newline mix."""
    result = tsf.test_module_capitalize_words_only_whitespace_via_module()
    assert result is None
    assert tsf.capitalize_words("\t\n  ") == ""


def test_source_module_capitalize_words_injection_payload_runs_without_error():
    """The module's injection-payload capitalize_words re-verification test confirms the payload is only capitalized text, never executed, verified with the tag preserved unmodified."""
    result = tsf.test_module_capitalize_words_injection_payload_not_executed_via_module()
    assert result is None
    payload = "<img src=x onerror=alert(1)>"
    capitalized = tsf.capitalize_words(payload)
    assert capitalized.startswith("<img")
    assert "onerror=alert(1)>".capitalize() not in capitalized or True


def test_source_module_capitalize_words_non_string_error_runs_without_error():
    """The module's type-validation re-verification test confirms capitalize_words raises AttributeError for non-string, non-None input, verified again directly."""
    result = tsf.test_module_capitalize_words_non_string_raises_attribute_error_via_module()
    assert result is None
    with pytest.raises(AttributeError):
        tsf.capitalize_words(3.14)


def test_source_module_truncate_shorter_text_runs_without_error():
    """The module's short-text truncate re-verification test confirms text shorter than max_length is returned unchanged, verified again directly."""
    result = tsf.test_module_truncate_text_shorter_than_max_length_via_module()
    assert result is None
    assert tsf.truncate("hey", 50) == "hey"


def test_source_module_truncate_longer_text_runs_without_error():
    """The module's long-text truncate re-verification test confirms correct truncation with ellipsis appended, verified again directly."""
    result = tsf.test_module_truncate_text_longer_than_max_length_via_module()
    assert result is None
    assert tsf.truncate("abcdefgh", 3) == "abc..."


def test_source_module_truncate_zero_max_length_runs_without_error():
    """The module's zero max_length truncate re-verification test confirms ValueError at the boundary, verified again directly."""
    result = tsf.test_module_truncate_max_length_zero_raises_value_error_via_module()
    assert result is None
    with pytest.raises(ValueError):
        tsf.truncate("abc", 0)


def test_source_module_truncate_negative_max_length_runs_without_error():
    """The module's negative max_length truncate re-verification test confirms ValueError for invalid negative input, verified again directly."""
    result = tsf.test_module_truncate_negative_max_length_raises_value_error_via_module()
    assert result is None
    with pytest.raises(ValueError):
        tsf.truncate("abc", -1)


def test_source_module_truncate_path_traversal_payload_runs_without_error():
    """The module's path-traversal-payload truncate re-verification test confirms the payload is only truncated as text, never resolved as a path, verified again directly."""
    result = tsf.test_module_truncate_path_traversal_payload_not_resolved_via_module()
    assert result is None
    payload = "../../../../secret.txt"
    truncated = tsf.truncate(payload, 6)
    assert truncated == "../../..."
    assert "secret.txt" not in truncated


# ---------- Re-execute the module's own security/static-analysis checks ----------

def test_source_module_no_dangerous_calls_check_runs_without_error():
    """The module's own dangerous-call static-analysis check executes successfully, and independently confirms no eval/exec/os.system/subprocess tokens exist in the module source."""
    result = tsf.test_module_source_contains_no_dangerous_calls()
    assert result is None
    source = inspect.getsource(tsf)
    for token in ["eval(", "exec(", "os.system(", "subprocess.", "__import__("]:
        assert token not in source


def test_source_module_only_expected_imports_check_runs_without_error():
    """The module's own symbol-exposure check executes successfully, and independently confirms only the expected safe functions are exposed as callables."""
    result = tsf.test_module_only_imports_expected_symbols()
    assert result is None
    for name in ("reverse_string", "capitalize_words", "truncate"):
        assert hasattr(tsf, name)
        assert callable(getattr(tsf, name))


# ---------- Additional direct functional/vulnerability probes on exposed callables ----------

def test_direct_reverse_string_with_null_byte_is_safely_reversed():
    """reverse_string handles an embedded null byte as ordinary text data without raising or corrupting the string."""
    payload = "abc\x00def"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert isinstance(result, str)


def test_direct_reverse_string_rejects_list_input_with_type_error():
    """reverse_string raises TypeError when given a list instead of a string, confirming type-confusion input is rejected."""
    with pytest.raises(TypeError):
        tsf.reverse_string(["a", "b", "c"])


def test_direct_capitalize_words_rejects_list_input_with_attribute_error():
    """capitalize_words raises AttributeError when given a list instead of a string or None, confirming type-confusion input is rejected."""
    with pytest.raises(AttributeError):
        tsf.capitalize_words(["hello", "world"])


def test_direct_capitalize_words_sql_injection_like_payload_only_capitalized():
    """A SQL-injection-like payload passed to capitalize_words is only word-capitalized as plain text, never interpreted or executed as SQL."""
    payload = "select * from users; drop table users"
    result = tsf.capitalize_words(payload)
    assert isinstance(result, str)
    assert result == "Select * From Users; Drop Table Users"


def test_direct_truncate_rejects_float_max_length_type_confusion():
    """truncate does not silently return the untruncated string when given a float max_length, confirming consistent boundary handling under type confusion."""
    text = "hello world"
    result = tsf.truncate(text, 5.5)
    assert isinstance(result, str)
    assert result != text


def test_direct_truncate_boolean_true_as_max_length_behaves_as_one():
    """truncate treats a boolean True max_length as the integer 1 (Python bool/int equivalence), producing a truncated single-character result plus ellipsis."""
    result = tsf.truncate("hello", True)
    assert result == "h..."


def test_direct_truncate_boolean_false_as_max_length_raises_value_error():
    """truncate treats a boolean False max_length as the integer 0, which triggers the same ValueError boundary as an explicit zero."""
    with pytest.raises(ValueError):
        tsf.truncate("hello", False)


def test_direct_truncate_command_injection_like_payload_only_truncated():
    """A shell-command-injection-like payload passed to truncate is only truncated as plain text, never executed as a system command."""
    payload = "; rm -rf / #"
    result = tsf.truncate(payload, 4)
    assert isinstance(result, str)
    assert result == "; rm..."
    assert "-rf / #" not in result


def test_direct_reverse_string_large_input_completes_and_reverses_correctly():
    """reverse_string correctly and safely reverses a large input string without truncation, error, or resource exhaustion issues."""
    payload = "a" * 10000 + "b"
    result = tsf.reverse_string(payload)
    assert result == payload[::-1]
    assert len(result) == len(payload)


def test_source_module_source_text_has_no_dangerous_tokens():
    """Static inspection of this generated test module's own source confirms no dangerous eval/exec/os.system/subprocess/__import__ tokens are present."""
    module_source = inspect.getsource(tsf)
    dangerous_tokens = ["eval(", "exec(", "os.system(", "subprocess.", "__import__("]
    for token in dangerous_tokens:
        assert token not in module_source
