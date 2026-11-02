from .models import Product


def search_products(products: list[Product], query: str = "", min_price: float | None = None,
                    max_price: float | None = None, active_only: bool = True) -> list[Product]:
    q = query.casefold().strip()
    result = []
    for product in products:
        if active_only and not product.active:
            continue
        if q and q not in product.name.casefold() and q not in product.sku.casefold():
            continue
        if min_price is not None and product.price < min_price:
            continue
        if max_price is not None and product.price > max_price:
            continue
        result.append(product)
    return result


def paginate(items: list, page: int = 1, page_size: int = 10) -> list:
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive")
    start = (page - 1) * page_size
    return items[start:start + page_size]
