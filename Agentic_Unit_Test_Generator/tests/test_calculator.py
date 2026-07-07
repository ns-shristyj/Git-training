import pytest
from Agentic_Unit_Test_Generator.scripts.calculator import Calculator


def test_add():
    calc = Calculator()

    # normal cases
    assert calc.add(1, 2) == 3
    assert calc.add(-1, 1) == 0
    assert calc.add(-1, -1) == -2
    assert calc.add(0, 0) == 0

    # input validation — None should raise TypeError, not return None
    with pytest.raises(TypeError):
        calc.add(None, 1)
    with pytest.raises(TypeError):
        calc.add(1, None)

    # wrong type
    with pytest.raises(TypeError):
        calc.add("1", 2)


def test_subtract():
    calc = Calculator()

    # normal cases
    assert calc.subtract(3, 2) == 1
    assert calc.subtract(1, -1) == 2
    assert calc.subtract(-1, 1) == -2
    assert calc.subtract(0, 0) == 0

    # input validation
    with pytest.raises(TypeError):
        calc.subtract(None, 1)
    with pytest.raises(TypeError):
        calc.subtract(1, None)

    # wrong type
    with pytest.raises(TypeError):
        calc.subtract("3", 2)


def test_multiply():
    calc = Calculator()

    # normal cases
    assert calc.multiply(3, 2) == 6
    assert calc.multiply(-1, 1) == -1
    assert calc.multiply(-1, -1) == 1
    assert calc.multiply(0, 5) == 0

    # input validation
    with pytest.raises(TypeError):
        calc.multiply(None, 1)
    with pytest.raises(TypeError):
        calc.multiply(1, None)

    # wrong type
    with pytest.raises(TypeError):
        calc.multiply("3", 2)


def test_divide():
    calc = Calculator()

    # normal cases
    assert calc.divide(6, 2) == 3
    assert calc.divide(-6, 2) == -3
    assert calc.divide(6, -2) == -3
    assert calc.divide(0, 1) == 0

    # divide by zero — must raise ValueError with correct message
    with pytest.raises(ValueError) as exc_info:
        calc.divide(1, 0)
    assert "Cannot divide by zero" in str(exc_info.value)

    # input validation
    with pytest.raises(TypeError):
        calc.divide(None, 1)
    with pytest.raises(TypeError):
        calc.divide(1, None)

    # wrong type
    with pytest.raises(TypeError):
        calc.divide("6", 2)