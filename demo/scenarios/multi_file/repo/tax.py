VAT_RATE = 0.15  # BUG: UK standard rate is 0.20


def vat_for(net_amount):
    return net_amount * VAT_RATE
