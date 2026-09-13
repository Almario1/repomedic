import unittest

from cart import checkout_total


class CheckoutTests(unittest.TestCase):
    def test_discounted_total_includes_vat_on_discounted_amount(self):
        # 100.00 - 10% = 90.00; 90.00 + 20% VAT = 108.00
        self.assertAlmostEqual(checkout_total(100.0), 108.0)

    def test_small_basket(self):
        # no discount: 50.00 + 20% VAT = 60.00
        self.assertAlmostEqual(checkout_total(50.0), 60.0)


if __name__ == "__main__":
    unittest.main()
