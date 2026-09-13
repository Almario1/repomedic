from compatlib import normalize


def order_key(customer_name, sku):
    return normalize(customer_name) + ":" + normalize(sku)
