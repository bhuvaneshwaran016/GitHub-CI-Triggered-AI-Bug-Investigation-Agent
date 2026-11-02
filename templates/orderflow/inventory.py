from .models import Product


class InventoryError(Exception):
    pass


class Inventory:
    def __init__(self):
        self._products: dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        if product.sku in self._products:
            raise InventoryError("duplicate SKU")
        if product.stock < 0 or product.price < 0:
            raise InventoryError("invalid product values")
        self._products[product.sku] = product

    def get(self, sku: str) -> Product:
        try:
            return self._products[sku]
        except KeyError:
            raise InventoryError(f"unknown SKU: {sku}") from None

    def reserve(self, sku: str, quantity: int) -> None:
        if quantity <= 0:
            raise InventoryError("quantity must be positive")
        product = self.get(sku)
        if product.stock < quantity:
            raise InventoryError("insufficient stock")
        product.stock -= quantity

    def release(self, sku: str, quantity: int) -> None:
        if quantity <= 0:
            raise InventoryError("quantity must be positive")
        product = self.get(sku)
        product.stock += quantity

    def all_products(self) -> list[Product]:
        return list(self._products.values())

