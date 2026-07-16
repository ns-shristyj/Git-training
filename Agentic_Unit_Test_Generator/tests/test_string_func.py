import pytest
from NIC_SecEng_Task.Calculator.string_func import (
    reverse_string,
    capitalize_words,
    truncate,
)


# ---------- reverse_string ----------

def test_reverse_string_basic():
    """Verifies basic string reversal works correctly."""
    assert reverse_string("hello") == "olleh"


def test_reverse_string_empty():
    """Verifies reversing an empty string returns an empty string."""
    assert reverse_string("") == ""


def test_reverse_string_single_char():
    """Verifies reversing a single character string returns the same character."""
    assert reverse_string("a") == "a"


def test_reverse_string_palindrome():
    """Verifies reversing a palindrome returns the same string."""
    assert reverse_string("racecar") == "racecar"


def test_reverse_string_with_spaces():
    """Verifies reversing a string with spaces preserves the spaces correctly."""
    assert reverse_string("a b c") == "c b a"


def test_reverse_string_unicode():
    """Verifies reversing a string with unicode characters works correctly."""
    assert reverse_string("héllo") == "olléh"


def test_reverse_string_special_chars_injection_like():
    """Verifies reversing a string containing injection-like payloads treats it as plain text."""
    payload = "<script>alert(1)</script>"
    result = reverse_string(payload)
    assert result == payload[::-1]
    # Ensure payload is not executed or altered semantically, just reversed text
    assert isinstance(result, str)


# ---------- capitalize_words ----------

def test_capitalize_words_basic():
    """Verifies each word's first letter is capitalized and rest lowercased."""
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_empty_string():
    """Verifies an empty string input returns an empty string."""
    assert capitalize_words("") == ""


def test_capitalize_words_none_like_falsy():
    """Verifies falsy input like empty string returns empty string without error."""
    assert capitalize_words("") == ""


def test_capitalize_words_multiple_spaces():
    """Verifies multiple spaces between words are collapsed to single spaces in output."""
    assert capitalize_words("hello    world") == "Hello World"


def test_capitalize_words_mixed_case():
    """Verifies mixed-case words are normalized to capitalized form."""
    assert capitalize_words("hELLo WoRLD") == "Hello World"


def test_capitalize_words_single_word():
    """Verifies a single word input is properly capitalized."""
    assert capitalize_words("python") == "Python"


def test_capitalize_words_leading_trailing_whitespace():
    """Verifies leading and trailing whitespace is stripped in the output."""
    assert capitalize_words("   hello world   ") == "Hello World"


def test_capitalize_words_numbers_and_symbols():
    """Verifies words containing numbers/symbols are handled without crashing."""
    result = capitalize_words("123abc test!")
    assert result == "123abc Test!"


def test_capitalize_words_injection_like_payload():
    """Verifies injection-like payload is treated as literal text and safely capitalized."""
    payload = "<script>alert(1)</script> test"
    result = capitalize_words(payload)
    assert result.startswith("<script>alert(1)</script>".capitalize())
    assert "Test" in result


# ---------- truncate ----------

def test_truncate_no_truncation_needed():
    """Verifies text shorter than max_length is returned unchanged."""
    assert truncate("hello", 10) == "hello"


def test_truncate_exact_length():
    """Verifies text exactly equal to max_length is returned unchanged without ellipsis."""
    assert truncate("hello", 5) == "hello"


def test_truncate_exceeds_length():
    """Verifies text exceeding max_length is truncated and ellipsis appended."""
    assert truncate("hello world", 5) == "hello..."


def test_truncate_zero_max_length_raises():
    """Verifies max_length of zero raises ValueError as it's not a positive integer."""
    with pytest.raises(ValueError):
        truncate("hello", 0)


def test_truncate_negative_max_length_raises():
    """Verifies negative max_length raises ValueError to prevent invalid truncation behavior."""
    with pytest.raises(ValueError):
        truncate("hello", -5)


def test_truncate_empty_text():
    """Verifies truncating an empty string with a positive max_length returns empty string."""
    assert truncate("", 5) == ""


def test_truncate_max_length_one():
    """Verifies truncation to length one works correctly with ellipsis appended."""
    assert truncate("hello", 1) == "h..."


def test_truncate_injection_like_payload():
    """Verifies truncation safely handles injection-like payloads without altering the security context."""
    payload = "<script>alert('xss')</script>"
    result = truncate(payload, 10)
    assert result == payload[:10] + "..."
    assert isinstance(result, str)


def test_truncate_path_traversal_like_payload():
    """Verifies truncation of path-traversal-like strings simply truncates text without special handling."""
    payload = "../../../../etc/passwd"
    result = truncate(payload, 5)
    assert result == "../.." + "..."
