import pytest
from NIC_SecEng_Task.Calculator.calculator import Calculator

def test_add():
    calc = Calculator()
    
    # Input validation
    assert calc.add(None, 1) is None
    assert calc.add(1, None) is None
    assert calc.add('', 1) is None
    assert calc.add(1, '') is None
    assert calc.add(1.5, 2) == 3.5
    assert calc.add(1, 2.5) == 3.5
    assert calc.add(-1, 1) == 0
    assert calc.add(1, -2) == -1
    assert calc.add(1, 2) == 3
    
    # Edge cases
    assert calc.add(0, 0) == 0
    assert calc.add(0, 1) == 1
    assert calc.add(-1, -1) == -2
    assert calc.add(1e100, 1e100) == 2e100
    
    # Error cases
    with pytest.raises(TypeError):
        calc.add('a', 1)
    with pytest.raises(TypeError):
        calc.add(1, 'b')

def test_subtract():
    calc = Calculator()
    
    # Input validation
    assert calc.subtract(None, 1) is None
    assert calc.subtract(1, None) is None
    assert calc.subtract('', 1) is None
    assert calc.subtract(1, '') is None
    assert calc.subtract(1.5, 2) == -0.5
    assert calc.subtract(1, 2.5) == -1.5
    assert calc.subtract(-1, 1) == -2
    assert calc.subtract(1, -2) == 3
    assert calc.subtract(1, 2) == -1
    
    # Edge cases
    assert calc.subtract(0, 0) == 0
    assert calc.subtract(0, 1) == -1
    assert calc.subtract(-1, -1) == 0
    assert calc.subtract(1e100, 1e100) == 0
    
    # Error cases
    with pytest.raises(TypeError):
        calc.subtract('a', 1)
    with pytest.raises(TypeError):
        calc.subtract(1, 'b')

def test_multiply():
    calc = Calculator()
    
    # Input validation
    assert calc.multiply(None, 1) is None
    assert calc.multiply(1, None) is None
    assert calc.multiply('', 1) is None
    assert calc.multiply(1, '') is None
    assert calc.multiply(1.5, 2) == 3
    assert calc.multiply(1, 2.5) == 2.5
    assert calc.multiply(-1, 1) == -1
    assert calc.multiply(1, -2) == -2
    assert calc.multiply(1, 2) == 2
    
    # Edge cases
    assert calc.multiply(0, 0) == 0
    assert calc.multiply(0, 1) == 0
    assert calc.multiply(-1, -1) == 1
    assert calc.multiply(1e100, 1e100) == 1e200
    
    # Error cases
    with pytest.raises(TypeError):
        calc.multiply('a', 1)
    with pytest.raises(TypeError):
        calc.multiply(1, 'b')

def test_divide():
    calc = Calculator()
    
    # Input validation
    assert calc.divide(None, 1) is None
    assert calc.divide(1, None) is None
    assert calc.divide('', 1) is None
    assert calc.divide(1, '') is None
    assert calc.divide(1.5, 2) == 0.75
    assert calc.divide(1, 2.5) == 0.4
    assert calc.divide(-1, 1) == -1
    assert calc.divide(1, -2) == -0.5
    assert calc.divide(1, 2) == 0.5
    
    # Edge cases
    assert calc.divide(0, 1) == 0
    assert calc.divide(1, 0) is None  # This will raise an exception, which is tested below
    
    # Error cases
    with pytest.raises(TypeError):
        calc.divide('a', 1)
    with pytest.raises(TypeError):
        calc.divide(1, 'b')
    
    # Division by zero
    with pytest.raises(ValueError) as exc_info:
        calc.divide(1, 0)
    assert str(exc_info.value) == "Cannot divide by zero!"
