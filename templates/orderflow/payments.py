class PaymentError(Exception):
    pass


class PaymentGateway:
    def __init__(self):
        self._charges: dict[str, float] = {}

    def charge(self, order_id: str, amount: float, idempotency_key: str) -> str:
        if amount <= 0:
            raise PaymentError("amount must be positive")
        if idempotency_key in self._charges:
            if self._charges[idempotency_key] != amount:
                raise PaymentError("idempotency key reused with different amount")
            return f"pay_{order_id}"
        self._charges[idempotency_key] = amount
        return f"pay_{order_id}"

    def refund(self, idempotency_key: str, amount: float) -> None:
        if idempotency_key not in self._charges:
            raise PaymentError("unknown payment")
        if amount <= 0:
            raise PaymentError("refund must be positive")
        self._charges[idempotency_key] -= amount
        if self._charges[idempotency_key] < 0:
            raise PaymentError("refund exceeds captured amount")

