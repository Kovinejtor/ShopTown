from fastapi import FastAPI
from models.product import Product
from services.product_service import create_products_table, get_products_table
from decimal import Decimal

app = FastAPI(title="ShopTown API")

@app.on_event("startup")
def startup_event():
    create_products_table()

@app.get("/")
def root():
    return {"message": "Dobrodošli u ShopTown!"}

@app.post("/products")
def create_product(product: Product):
    table = get_products_table()

    item = product.dict()
    item['price'] = Decimal(str(item['price'])) 
    
    table.put_item(Item=item)
    return {"message": "Proizvod dodan!", "product": product}

@app.get("/products")
def list_products():
    table = get_products_table()
    response = table.scan()
    return {"products": response.get('Items', [])}
