from decimal import Decimal
from pydantic import BaseModel

class Review(BaseModel):
    review_id: str
    product_id: str 
    user_id: str
    rating: Decimal
    review: str