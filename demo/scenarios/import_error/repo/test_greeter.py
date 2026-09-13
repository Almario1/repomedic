import unittest

from greeter import greet


class GreeterTests(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ada", "Lovelace"), "Good evening, Lovelace, Ada")


if __name__ == "__main__":
    unittest.main()
