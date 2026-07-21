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
        (2.5, 3.5, 6.0),
    ])
    def test_add_functionality(self, calc, a, b, expected):
        """Verify add() correctly sums typical integer, negative, zero, and float inputs."""
        assert calc.add(a, b) == expected

    def test_add_invalid_type_raises_type_error(self, calc):
        """Verify add() raises TypeError when adding incompatible types (int + str)."""
        with pytest.raises(TypeError):
            calc.add(1, "a")


class TestSubtract:
    @pytest.mark.parametrize("a, b, expected", [
        (5, 3, 2),
        (0, 5, -5),
        (2.5, 0.5, 2.0),
    ])
    def test_subtract_functionality(self, calc, a, b, expected):
        """Verify subtract() correctly computes difference for typical, zero, and float inputs."""
        assert calc.subtract(a, b) == expected

    def test_subtract_invalid_type_raises_type_error(self, calc):
        """Verify subtract() raises TypeError when subtracting incompatible types (int - str)."""
        with pytest.raises(TypeError):
            calc.subtract(1, "a")


class TestMultiply:
    @pytest.mark.parametrize("a, b, expected", [
        (3, 4, 12),
        (-2, 3, -6),
        (0, 100, 0),
        (2.5, 2, 5.0),
    ])
    def test_multiply_functionality(self, calc, a, b, expected):
        """Verify multiply() correctly computes product for typical, negative, zero, and float inputs."""
        assert calc.multiply(a, b) == expected

    def test_multiply_invalid_type_raises_type_error(self, calc):
        """Verify multiply() raises TypeError when multiplying incompatible types (int * None)."""
        with pytest.raises(TypeError):
            calc.multiply(1, None)


class TestDivide:
    @pytest.mark.parametrize("a, b, expected", [
        (10, 2, 5.0),
        (-9, 3, -3.0),
        (7, 2, 3.5),
    ])
    def test_divide_functionality(self, calc, a, b, expected):
        """Verify divide() correctly computes quotient for typical positive, negative, and non-integer results."""
        assert calc.divide(a, b) == expected

    def test_divide_by_zero_raises_value_error(self, calc):
        """Verify divide() raises ValueError with correct message when dividing by zero (edge-case guard)."""
        with pytest.raises(ValueError, match="Cannot divide by 0!"):
            calc.divide(10, 0)

    def test_divide_invalid_type_raises_type_error(self, calc):
        """Verify divide() raises TypeError when dividing incompatible types (str / int), since no type guard exists."""
        with pytest.raises(TypeError):
            calc.divide("10", 2)
