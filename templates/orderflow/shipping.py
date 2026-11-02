def shipping_fee(subtotal_after_discount: float, item_count: int, country: str = "US") -> float:
    if subtotal_after_discount < 0 or item_count < 0:
        raise ValueError("invalid shipping inputs")
    if country.upper() != "US":
        return 25.00
    if subtotal_after_discount >= 100:
        return 0.0
    if item_count >= 5:
        return 4.99
    return 7.99