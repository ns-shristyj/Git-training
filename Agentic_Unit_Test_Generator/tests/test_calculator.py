from Agentic_Unit_Test_Generator.scripts.calculator import Calculator

def test_add():
    calc = Calculator()
    assert calc.add(1, 2) == 3
    assert calc.add(-1, 1) == 0
    assert calc.add(0, 0) == 0
    assert calc.add(1e308, 1) == 1e308 + 1  # Edge case: large numbers
    with pytest.raises(TypeError):
        calc.add("a", 1)
    with pytest.raises(TypeError):
        calc.add(None, 1)

def test_subtract():
    calc = Calculator()
    assert calc.subtract(2, 1) == 1
    assert calc.subtract(1, 1) == 0
    assert calc.subtract(0, 0) == 0
    assert calc.subtract(1e308, 1) == 1e308 - 1  # Edge case: large numbers
    with pytest.raises(TypeError):
        calc.subtract("a", 1)
    with pytest.raises(TypeError):
        calc.subtract(None, 1)

def test_multiply():
    calc = Calculator()
    assert calc.multiply(2, 3) == 6
    assert calc.multiply(0, 100) == 0
    assert calc.multiply(1e308, 2) == 1e308 * 2  # Edge case: large numbers
    with pytest.raises(TypeError):
        calc.multiply("a", 1)
    with pytest.raises(TypeError):
        calc.multiply(None, 1)

def test_divide():
    calc = Calculator()
    assert calc.divide(6, 3) == 2
    assert calc.divide(1, 1) == 1
    assert calc.divide(0, 1) == 0
    assert calc.divide(1e308, 1) == 1e308  # Edge case: large numbers
    with pytest.raises(ValueError) as exc_info:
        calc.divide(1, 0)
    assert str(exc_info.value) == "Cannot divide by zero!"
    with pytest.raises(TypeError):
        calc.divide("a", 1)
    with pytest.raises(TypeError):
        calc.divide(None, 1)
