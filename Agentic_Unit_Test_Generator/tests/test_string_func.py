import pytest

from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# --- reverse_string ---

def test_reverse_string_happy_path():
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    assert reverse_string("") == ""


def test_reverse_string_unicode_rtl_override():
    text = "abc\u202edef"
    assert reverse_string(text) == text[::-1]


def test_reverse_string_oversized_input():
    text = "a" * 10000
    result = reverse_string(text)
    assert result == text[::-1]
    assert len(result) == 10000


def test_reverse_string_type_confusion_raises_attributeerror():
    with pytest.raises(TypeError):
        reverse_string(12345)


# --- capitalize_words ---

def test_capitalize_words_happy_path():
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    assert capitalize_words("") == ""


def test_capitalize_words_none_returns_empty():
    assert capitalize_words(None) == ""


def test_capitalize_words_malicious_sql_injection_payload():
    payload = "' or 1=1--"
    result = capitalize_words(payload)
    assert result == "' Or 1=1--"


def test_capitalize_words_whitespace_only_returns_empty():
    assert capitalize_words("   \t\n  ") == ""


# --- truncate ---

def test_truncate_happy_path_no_truncation_needed():
    assert truncate("hello", 10) == "hello"


def test_truncate_exceeds_length_appends_ellipsis():
    assert truncate("hello world", 5) == "hello..."


def test_truncate_boundary_exact_length_no_ellipsis():
    text = "hello"
    assert truncate(text, len(text)) == text


def test_truncate_zero_max_length_raises_valueerror():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises_valueerror():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", -5)


def test_truncate_oversized_input_dos_probe():
    text = "a" * 10000
    result = truncate(text, 100)
    assert result == "a" * 100 + "..."
    assert len(result) == 103
