import pytest
from calculator import Calculator

@pytest.fixture
def calc():
    return Calculator()

def test_add(calc):
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0

def test_subtract(calc):
    assert calc.subtract(10, 5) == 5
    assert calc.subtract(0, 5) == -5

def test_multiply(calc):
    assert calc.multiply(3, 4) == 12
    assert calc.multiply(-2, 3) == -6

def test_divide(calc):
    assert calc.divide(10, 2) == 5
    
    with pytest.raises(ValueError):
        calc.divide(9, 0)