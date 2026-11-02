from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class Product:
    sku: str
    name: str
    price: float
    stock: int
    active: bool = True


@dataclass
class OrderItem:
    sku: str
    quantity: int
    unit_price: float


@dataclass
class Order:
    order_id: str
    customer_id: str
    items: list[OrderItem]
    subtotal: float
    discount: float
    tax: float
    shipping: float  # Fixed typo from 'shipping' to 'shipping'
    total: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payment_reference: Optional[str] = None
    refund_total: float = 0.0