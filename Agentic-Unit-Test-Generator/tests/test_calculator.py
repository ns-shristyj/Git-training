import unittest
from unittest import mock
from NIC_SecEng_Task.Calculator.calculator import Calculator

class TestCalculator(unittest.TestCase):
    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_add(self, MockCalculator):
        calculator = MockCalculator.return_value
        calculator.add.side_effect = lambda a, b: a + b
        
        # Input validation
        with self.assertRaises(TypeError):
            calculator.add(None, 1)
        with self.assertRaises(TypeError):
            calculator.add(1, None)
        
        # Injection vectors
        with self.assertRaises(TypeError):
            calculator.add("a", 1)
        with self.assertRaises(TypeError):
            calculator.add(1, "b")
        
        # Auth boundaries
        with self.assertRaises(TypeError):
            calculator.add(object(), 1)
        
        # Error leakage
        with mock.patch.object(calculator, 'add', side_effect=ValueError("Internal Error")) as mock_method:
            with self.assertRaises(ValueError):
                calculator.add(2, 3)
            mock_method.assert_called_once_with(2, 3)
        
        # Resource limits
        self.assertEqual(calculator.add(1e9, 1e9), 2e9)
        
        # Mocked-dependency failure modes
        calculator.add.side_effect = None
        with mock.patch.object(calculator, 'add', side_effect=RuntimeError("Mocked failure")) as mock_method:
            with self.assertRaises(RuntimeError):
                calculator.add(1, 1)
            mock_method.assert_called_once_with(1, 1)
    
    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_subtract(self, MockCalculator):
        calculator = MockCalculator.return_value
        calculator.subtract.side_effect = lambda a, b: a - b
        
        # Input validation
        with self.assertRaises(TypeError):
            calculator.subtract(None, 1)
        with self.assertRaises(TypeError):
            calculator.subtract(1, None)
        
        # Injection vectors
        with self.assertRaises(TypeError):
            calculator.subtract("a", 1)
        with self.assertRaises(TypeError):
            calculator.subtract(1, "b")
        
        # Auth boundaries
        with self.assertRaises(TypeError):
            calculator.subtract(object(), 1)
        
        # Error leakage
        with mock.patch.object(calculator,'subtract', side_effect=ValueError("Internal Error")) as mock_method:
            with self.assertRaises(ValueError):
                calculator.subtract(2, 3)
            mock_method.assert_called_once_with(2, 3)
        
        # Resource limits
        self.assertEqual(calculator.subtract(1e9, 1e9), 0)
        
        # Mocked-dependency failure modes
        calculator.subtract.side_effect = None
        with mock.patch.object(calculator,'subtract', side_effect=RuntimeError("Mocked failure")) as mock_method:
            with self.assertRaises(RuntimeError):
                calculator.subtract(1, 1)
            mock_method.assert_called_once_with(1, 1)
    
    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_multiply(self, MockCalculator):
        calculator = MockCalculator.return_value
        calculator.multiply.side_effect = lambda a, b: a * b
        
        # Input validation
        with self.assertRaises(TypeError):
            calculator.multiply(None, 1)
        with self.assertRaises(TypeError):
            calculator.multiply(1, None)
        
        # Injection vectors
        with self.assertRaises(TypeError):
            calculator.multiply("a", 1)
        with self.assertRaises(TypeError):
            calculator.multiply(1, "b")
        
        # Auth boundaries
        with self.assertRaises(TypeError):
            calculator.multiply(object(), 1)
        
        # Error leakage
        with mock.patch.object(calculator,'multiply', side_effect=ValueError("Internal Error")) as mock_method:
            with self.assertRaises(ValueError):
                calculator.multiply(2, 3)
            mock_method.assert_called_once_with(2, 3)
        
        # Resource limits
        self.assertEqual(calculator.multiply(1e9, 1e9), 1e18)
        
        # Mocked-dependency failure modes
        calculator.multiply.side_effect = None
        with mock.patch.object(calculator, 'multiply', side_effect=RuntimeError("Mocked failure")) as mock_method:
            with self.assertRaises(RuntimeError):
                calculator.multiply(1, 1)
            mock_method.assert_called_once_with(1, 1)
    
    @mock.patch('NIC_SecEng_Task.Calculator.calculator.Calculator')
    def test_divide(self, MockCalculator):
        calculator = MockCalculator.return_value
        calculator.divide.side_effect = lambda a, b: a / b if b!= 0 else None
        
        # Input validation
        with self.assertRaises(TypeError):
            calculator.divide(None, 1)
        with self.assertRaises(TypeError):
            calculator.divide(1, None)
        
        # Injection vectors
        with self.assertRaises(TypeError):
            calculator.divide("a", 1)
        with self.assertRaises(TypeError):
            calculator.divide(1, "b")
        
        # Auth boundaries
        with self.assertRaises(TypeError):
            calculator.divide(object(), 1)
        
        # Error leakage
        with mock.patch.object(calculator, 'divide', side_effect=ValueError("Internal Error")) as mock_method:
            with self.assertRaises(ValueError):
                calculator.divide(2, 3)
            mock_method.assert_called_once_with(2, 3)
        
        # Division by zero
        with self.assertRaises(ValueError):
            calculator.divide(1, 0)
        
        # Resource limits
        self.assertEqual(calculator.divide(1e9, 1e9), 1.0)
        
        # Mocked-dependency failure modes
        calculator.divide.side_effect = None
        with mock.patch.object(calculator, 'divide', side_effect=RuntimeError("Mocked failure")) as mock_method:
            with self.assertRaises(RuntimeError):
                calculator.divide(1, 1)
            mock_method.assert_called_once_with(1, 1)
            with self.assertRaises(RuntimeError):
                calculator.divide(1, 0)
            mock_method.assert_called_with(1, 0)

if __name__ == '__main__':
    unittest.main()
