import pytest
from NIC_SecEng_Task.Calculator.calculator import Calculator


@pytest.fixture
def calc():
    return Calculator()


class TestAdd:
    @pytest.mark.parametrize("a, b, expected", [
        (2, 3, 5),
        (-1, 1, 0),
        (0, 0, 0),
        (2.5, 2.5, 5.0),
    ])
    def test_add_typical_values(self, calc, a, b, expected):
        """Verify add() correctly sums integers, negatives, zeros, and floats."""
        assert calc.add(a, b) == expected

    def test_add_invalid_types_raises_type_error(self, calc):
        """Verify add() raises TypeError when adding incompatible types (str + int)."""
        with pytest.raises(TypeError):
            calc.add("5", 3)


class TestSubtract:
    @pytest.mark.parametrize("a, b, expected", [
        (5, 3, 2),
        (0, 0, 0),
        (-1, -1, 0),
        (2.5, 0.5, 2.0),
    ])
    def test_subtract_typical_values(self, calc, a, b, expected):
        """Verify subtract() correctly computes difference for ints, negatives, and floats."""
        assert calc.subtract(a, b) == expected

    def test_subtract_invalid_types_raises_type_error(self, calc):
        """Verify subtract() raises TypeError when subtracting incompatible types (str - int)."""
        with pytest.raises(TypeError):
            calc.subtract("5", 3)


class TestMultiply:
    @pytest.mark.parametrize("a, b, expected", [
        (3, 4, 12),
        (0, 5, 0),
        (-2, 3, -6),
        (2.5, 2, 5.0),
    ])
    def test_multiply_typical_values(self, calc, a, b, expected):
        """Verify multiply() correctly computes product for ints, zero, negatives, and floats."""
        assert calc.multiply(a, b) == expected

    def test_multiply_invalid_types_raises_type_error(self, calc):
        """Verify multiply() raises TypeError when multiplying incompatible types (dict * int)."""
        with pytest.raises(TypeError):
            calc.multiply({"a": 1}, 3)


class TestDivide:
    @pytest.mark.parametrize("a, b, expected", [
        (10, 2, 5.0),
        (-9, 3, -3.0),
        (7, 2, 3.5),
    ])
    def test_divide_typical_values(self, calc, a, b, expected):
        """Verify divide() correctly performs true division for various numeric inputs."""
        assert calc.divide(a, b) == expected

    def test_divide_by_zero_raises_value_error(self, calc):
        """Verify divide() raises ValueError with correct message when dividing by zero."""
        with pytest.raises(ValueError, match="Cannot divide by 0!"):
            calc.divide(10, 0)

    def test_divide_invalid_types_raises_type_error(self, calc):
        """Verify divide() raises TypeError when dividing incompatible types (str / int)."""
        with pytest.raises(TypeError):
            calc.divide("10", 2)
