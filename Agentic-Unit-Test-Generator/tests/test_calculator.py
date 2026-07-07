import unittest
from unittest import mock
from NIC_SecEng_Task.Calculator.calculator import Calculator

class TestCalculator(unittest.TestCase):
    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_add(self, MockCalculator):
        instance = MockCalculator.return_value
        instance.add.side_effect = lambda a, b: a + b
        calculator = Calculator()

        # Input validation
        self.assertEqual(calculator.add(1, 2), 3)
        self.assertEqual(calculator.add(-1, 1), 0)
        self.assertEqual(calculator.add(-1, -1), -2)
        self.assertEqual(calculator.add(0, 0), 0)

        # Injection vectors
        self.assertEqual(calculator.add('1', '2'), '12')  # Not a true injection, but checks for type handling

        # Auth boundaries (N/A for this function)

        # Error leakage (N/A for this function)

        # Resource limits (N/A for this function)

        # Mocked-dependency failure modes (N/A for this function)

    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_subtract(self, MockCalculator):
        instance = MockCalculator.return_value
        instance.subtract.side_effect = lambda a, b: a - b
        calculator = Calculator()

        # Input validation
        self.assertEqual(calculator.subtract(3, 2), 1)
        self.assertEqual(calculator.subtract(1, -1), 2)
        self.assertEqual(calculator.subtract(-1, 1), -2)
        self.assertEqual(calculator.subtract(0, 0), 0)

        # Injection vectors
        self.assertEqual(calculator.subtract('3', '2'), '1')  # Not a true injection, but checks for type handling

        # Auth boundaries (N/A for this function)

        # Error leakage (N/A for this function)

        # Resource limits (N/A for this function)

        # Mocked-dependency failure modes (N/A for this function)

    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_multiply(self, MockCalculator):
        instance = MockCalculator.return_value
        instance.multiply.side_effect = lambda a, b: a * b
        calculator = Calculator()

        # Input validation
        self.assertEqual(calculator.multiply(3, 2), 6)
        self.assertEqual(calculator.multiply(-1, 1), -1)
        self.assertEqual(calculator.multiply(-1, -1), 1)
        self.assertEqual(calculator.multiply(0, 5), 0)

        # Injection vectors
        self.assertEqual(calculator.multiply('3', '2'), '32')  # Not a true injection, but checks for type handling

        # Auth boundaries (N/A for this function)

        # Error leakage (N/A for this function)

        # Resource limits (N/A for this function)

        # Mocked-dependency failure modes (N/A for this function)

    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_divide(self, MockCalculator):
        instance = MockCalculator.return_value
        instance.divide.side_effect = lambda a, b: a / b if b!= 0 else None
        calculator = Calculator()

        # Input validation
        self.assertEqual(calculator.divide(6, 2), 3)
        self.assertEqual(calculator.divide(-6, 2), -3)
        self.assertEqual(calculator.divide(6, -2), -3)
        self.assertEqual(calculator.divide(0, 1), 0)

        # Injection vectors
        self.assertIsNone(calculator.divide('6', '2'))  # Not a true injection, but checks for type handling

        # Auth boundaries (N/A for this function)

        # Error leakage
        with self.assertRaises(ValueError):
            calculator.divide(1, 0)

        # Resource limits (N/A for this function)

        # Mocked-dependency failure modes (N/A for this function)

if __name__ == '__main__':
    unittest.main()
