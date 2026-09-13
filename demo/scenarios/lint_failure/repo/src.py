def shout(message):
    return message.upper() + "!"


def banner(message, width):
    line = shout(message)  
    return line.center(width)


def describe(item_count, warehouse_name, region_code, expedited, gift_wrap, insurance_level):
    flags = []
    if expedited:
        flags.append("expedited")
    if gift_wrap:
        flags.append("gift")
    return f"{item_count} items from {warehouse_name}/{region_code} [{flags}] insurance={insurance_level}"
