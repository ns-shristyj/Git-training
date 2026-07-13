import pytest
from NIC_SecEng_Task.Calculator.string_func import reverse_string, capitalize_words, truncate


# ── reverse_string ────────────────────────────────────────────────────────────

def test_reverse_string_basic():
    assert reverse_string("hello") == "olleh"

def test_reverse_string_empty():
    assert reverse_string("") == ""

def test_reverse_string_sql_injection():
    payload = "' OR 1=1--"
    assert reverse_string(payload) == payload[::-1]

def test_reverse_string_unicode_rtl_override():
    # U+202E right-to-left override — must survive round-trip reversal
    text = "abc\u202Edef"
    assert reverse_string(text) == "fed\u202Ecba"

def test_reverse_string_oversized():
    big = "A" * 10_000
    assert reverse_string(big) == big  # palindrome of single char

def test_reverse_string_null_byte():
    text = "ab\x00cd"
    assert reverse_string(text) == "dc\x00ba"


# ── capitalize_words ──────────────────────────────────────────────────────────

def test_capitalize_words_basic():
    assert capitalize_words("hello world") == "Hello World"

def test_capitalize_words_empty():
    assert capitalize_words("") == ""

def test_capitalize_words_none_raises():
    with pytest.raises((AttributeError, TypeError)):
        capitalize_words(None)  # type: ignore[arg-type]

def test_capitalize_words_path_traversal():
    # adversarial path-like input — should not crash, just capitalize tokens
    result = capitalize_words("../../../etc/passwd")
    assert result == "../../../Etc/Passwd"

def test_capitalize_words_unicode_zero_width():
    # zero-width space U+200B between words
    text = "hello\u200Bworld"
    # split() treats zero-width space as part of the token, not whitespace
    result = capitalize_words(text)
    assert isinstance(result, str)
    assert len(result) > 0

def test_capitalize_words_extra_whitespace():
    # split() collapses multiple spaces; rejoined with single space
    assert capitalize_words("  foo   bar  ") == "Foo Bar"


# ── truncate ──────────────────────────────────────────────────────────────────

def test_truncate_basic_no_ellipsis():
    assert truncate("hello", 10) == "hello"

def test_truncate_exceeds_max_length():
    assert truncate("hello world", 5) == "hello..."

def test_truncate_exact_length():
    assert truncate("hello", 5) == "hello"

def test_truncate_zero_max_length_raises():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", 0)

def test_truncate_negative_max_length_raises():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", -1)

def test_truncate_max_length_wrong_type_raises():
    with pytest.raises((TypeError, ValueError)):
        truncate("hello", "five")  # type: ignore[arg-type]

def test_truncate_shell_metacharacters():
    payload = "$(rm -rf /); echo pwned"
    result = truncate(payload, 5)
    assert result == "$(rm ..."
    assert len(result) == 8  # 5 chars + "..."

def test_truncate_oversized_input():
    big = "x" * 10_000
    result = truncate(big, 100)
    assert result == "x" * 100 + "..."

def test_truncate_empty_string():
    # empty string length (0) <= any positive max_length
    assert truncate("", 5) == ""

def test_truncate_null_byte_in_text():
    text = "ab\x00cd"
    assert truncate(text, 3) == "ab\x00..."
