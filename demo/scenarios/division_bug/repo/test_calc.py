import unittest

from calc import add, divide, multiply, subtract


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(subtract(7, 2), 5)

    def test_multiply(self):
        self.assertEqual(multiply(4, 3), 12)

    def test_divide(self):
        self.assertEqual(divide(8, 2), 4)

    def test_divide_float(self):
        self.assertAlmostEqual(divide(7, 2), 3.5)


if __name__ == "__main__":
    unittest.main()
