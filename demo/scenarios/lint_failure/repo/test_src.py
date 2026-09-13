import unittest

from src import banner, describe, shout


class SrcTests(unittest.TestCase):
    def test_shout(self):
        self.assertEqual(shout("hi"), "HI!")

    def test_banner(self):
        self.assertEqual(banner("hi", 8), "  HI!   ")

    def test_describe(self):
        out = describe(2, "LON1", "UK", True, False, "standard")
        self.assertIn("expedited", out)


if __name__ == "__main__":
    unittest.main()
