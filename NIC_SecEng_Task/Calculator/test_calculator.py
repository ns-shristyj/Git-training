import unittest
from calculator import Calculator

class TestCalculator(unittest.TestCase):
    
    # This runs before every individual test method
    def setUp(self):
        self.calc = Calculator()

    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)
        self.assertEqual(self.calc.add(-1, 1), 0)

    def test_subtract(self):
        self.assertEqual(self.calc.subtract(10, 5), 5)
        self.assertEqual(self.calc.subtract(0, 5), -5)

    def test_multiply(self):
        self.assertEqual(self.calc.multiply(3, 4), 12)
        self.assertEqual(self.calc.multiply(-2, 3), -6)

    def test_divide(self):
        self.assertEqual(self.calc.divide(10, 2), 5)
        
        # Test that dividing by zero raises the correct error
        with self.assertRaises(ValueError):
            self.calc.divide(9, 0)

if __name__ == '__main__':
    unittest.main()