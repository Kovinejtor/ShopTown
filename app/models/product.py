from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

class ProductCreate(BaseModel):
    name: str
    description: str
    price: Decimal
    stock: int

class Product(ProductCreate):
    id: str
    seller_id: str
    review_ids: Optional[List[str]] = []  