import pytest
from NIC_SecEng_Task.Calculator.string_utils import reverse_string, capitalize_words, truncate

def test_reverse_string_none():
    with pytest.raises(TypeError):
        reverse_string(None)

def test_reverse_string_not_str():
    with pytest.raises(TypeError):
        reverse_string(123)

def test_reverse_string_empty():
    assert reverse_string("") == ""

def test_reverse_string_single_char():
    assert reverse_string("a") == "a"

def test_reverse_string_multi_char():
    assert reverse_string("hello") == "olleh"

def test_capitalize_words_none():
    with pytest.raises(TypeError):
        capitalize_words(None)

def test_capitalize_words_not_str():
    with pytest.raises(TypeError):
        capitalize_words(123)

def test_capitalize_words_empty():
    assert capitalize_words("") == ""

def test_capitalize_words_single_word():
    assert capitalize_words("hello") == "Hello"

def test_capitalize_words_multi_words():
    assert capitalize_words("hello world") == "Hello World"

def test_truncate_none():
    with pytest.raises(TypeError):
        truncate(None, 5)

def test_truncate_not_str():
    with pytest.raises(TypeError):
        truncate("hello", None)

def test_truncate_max_length_zero():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", 0)

def test_truncate_max_length_negative():
    with pytest.raises(ValueError, match="Maximum length must be a positive integer."):
        truncate("hello", -5)

def test_truncate_text_shorter():
    assert truncate("hello", 10) == "hello"

def test_truncate_text_longer():
    assert truncate("hello", 3) == "he..."

def test_truncate_text_boundary():
    assert truncate("hello", 5) == "hell..."
