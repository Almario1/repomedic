from tax import vat_for

DISCOUNT_THRESHOLD = 100.0
DISCOUNT_RATE = 0.10


def checkout_total(net_amount):
    discounted = net_amount
    if net_amount >= DISCOUNT_THRESHOLD:
        discounted = net_amount * (1 - DISCOUNT_RATE)
    return discounted + vat_for(net_amount)  # BUG: VAT on pre-discount amount
