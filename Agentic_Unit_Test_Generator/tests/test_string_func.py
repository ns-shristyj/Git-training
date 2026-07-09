import pytest
from NIC_SecEng_Task.Calculator.string_func import reverse_string, capitalize_words, truncate

def test_reverse_string_none():
    with pytest.raises(TypeError):
        reverse_string(None)

def test_reverse_string_empty():
    assert reverse_string("") == ""

def test_reverse_string_single_char():
    assert reverse_string("a") == "a"

def test_reverse_string_multiple_chars():
    assert reverse_string("hello") == "olleh"

def test_reverse_string_whitespace():
    assert reverse_string("   ") == "   "

def test_capitalize_words_none():
    with pytest.raises(TypeError):
        capitalize_words(None)

def test_capitalize_words_empty():
    assert capitalize_words("") == ""

def test_capitalize_words_single_word():
    assert capitalize_words("hello") == "Hello"

def test_capitalize_words_multiple_words():
    assert capitalize_words("hello world") == "Hello World"

def test_capitalize_words_multiple_words_with_punctuation():
    assert capitalize_words("hello, world!") == "Hello, World!"

def test_truncate_none():
    with pytest.raises(TypeError):
        truncate(None, 5)

def test_truncate_empty():
    assert truncate("", 5) == ""

def test_truncate_single_char():
    assert truncate("a", 5) == "a"

def test_truncate_within_limit():
    assert truncate("hello", 5) == "hello"

def test_truncate_exceeds_limit():
    assert truncate("hello", 3) == "he..."

def test_truncate_equal_limit():
    assert truncate("hello", 5) == "hello"

def test_truncate_negative_length():
    with pytest.raises(ValueError) as excinfo:
        truncate("hello", -1)
    assert str(excinfo.value) == "Maximum length must be a positive integer."
