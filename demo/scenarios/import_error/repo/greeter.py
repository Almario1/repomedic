from names import formal_name  # BUG: names.formal was renamed without an alias


def greet(first, last):
    return "Good evening, " + formal_name(first, last)
