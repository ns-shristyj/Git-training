from Agentic_Unit_Test_Generator.scripts.calculator import Calculator

def test_add():
    calc = Calculator()
    assert calc.add(1, 2) == 3
    assert calc.add(-1, 1) == 0
    assert calc.add(0, 0) == 0
    assert calc.add(-1, -1) == -2
    assert calc.add(1e10, 2e10) == 3e10

def test_subtract():
    calc = Calculator()
    assert calc.subtract(2, 1) == 1
    assert calc.subtract(1, 2) == -1
    assert calc.subtract(0, 0) == 0
    assert calc.subtract(0, 1) == -1
    assert calc.subtract(-1, -1) == 0
    assert calc.subtract(1e10, 2e10) == -1e10

def test_multiply():
    calc = Calculator()
    assert calc.multiply(2, 3) == 6
    assert calc.multiply(-1, 1) == -1
    assert calc.multiply(0, 100) == 0
    assert calc.multiply(1, 0) == 0
    assert calc.multiply(-1, -1) == 1
    assert calc.multiply(1e5, 1e5) == 1e10

def test_divide():
    calc = Calculator()
    assert calc.divide(6, 3) == 2
    assert calc.divide(1, 1) == 1
    assert calc.divide(0, 1) == 0
    assert calc.divide(1, -1) == -1
    assert calc.divide(-1, -1) == 1
    assert calc.divide(1e10, 2e9) == 5.0

    with pytest.raises(ValueError) as excinfo:
        calc.divide(1, 0)
    assert str(excinfo.value) == "Cannot divide by zero!"
