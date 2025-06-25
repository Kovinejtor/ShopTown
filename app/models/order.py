from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, Literal

class OrderCreate(BaseModel):
    buyer_id: str
    product_id: str
    product_name: str
    product_price: Decimal
    description: Optional[str]
    purchase_date: str  # ISO format string
    quantity: int
    total_price: Decimal
    seller_id: str
    status: Literal["completed", "refunded"]
    review_id: Optional[str] = None

class Order(OrderCreate):
    id: str