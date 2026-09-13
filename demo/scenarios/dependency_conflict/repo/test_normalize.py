import unittest

from normalize_order import order_key


class NormalizeTests(unittest.TestCase):
    def test_order_key_normalizes(self):
        # compatlib 2.0 normalize: strip, lowercase, drop - . _
        self.assertEqual(order_key("  ACME Corp.  ", "SKU-8891_A"), "acme corp:sku8891a")


if __name__ == "__main__":
    unittest.main()
