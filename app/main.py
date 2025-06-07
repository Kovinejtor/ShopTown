from fastapi import FastAPI
from models.product import Product, ProductCreate
from services.product_service import create_products_table, get_products_table
from decimal import Decimal
from utils.fill_dummy_data import populate_products_from_csv
from utils.delete_all_products import delete_all_products
import uuid

app = FastAPI(title="ShopTown API")

@app.on_event("startup")
def startup_event():
    create_products_table()

@app.get("/")
def root():
    return {"message": "Welcome to ShopTown!"}

@app.post("/populate")
def populate():
    populate_products_from_csv(100) 
    return {"message": "Dummy products added."}

@app.delete("/delete-all-products")
def delete_all():
    delete_all_products()
    return {"message": "All products deleted."}

@app.post("/products")
def create_product(product_data: ProductCreate):
    table = get_products_table()

    item = product_data.dict()
    item['id'] = str(uuid.uuid4())

    item['price'] = Decimal(str(item['price']))

    table.put_item(Item=item)
    return {"message": "Product added!", "product": item}

@app.get("/products")
def list_products():
    table = get_products_table()
    response = table.scan()
    return {"products": response.get('Items', [])}
