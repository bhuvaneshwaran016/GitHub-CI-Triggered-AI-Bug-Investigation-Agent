from decimal import Decimal, ROUND_HALF_UP


def money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_discount(subtotal: float, code: str | None = None) -> float:
    if subtotal < 0:
        raise ValueError("subtotal cannot be negative")
    if code is None:
        return 0.0
    normalized = code.strip().upper()
    if normalized == "SAVE10":
        return money(subtotal * 0.10)
    if normalized == "SAVE20":
        return money(subtotal * 0.20)
    raise ValueError("invalid discount code")


def calculate_tax(taxable_amount: float, tax_rate: float = 0.08) -> float:
    if taxable_amount < 0 or not 0 <= tax_rate <= 1:
        raise ValueError("invalid tax inputs")
    return money(taxable_amount * tax_rate)


def calculate_total(subtotal: float, discount: float, tax: float, shipping: float) -> float:
    return money(subtotal - discount + tax + shipping)

