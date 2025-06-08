from fastapi import FastAPI, Query
from models.product import Product, ProductCreate
from services.user_service import ensure_users_table_exists, get_users_table
from services.product_service import ensure_products_table_exists, get_products_table, get_products_by_seller
from services.order_service import ensure_orders_table_exists, purchase_product, get_orders_by_buyer
from decimal import Decimal
from utils.fill_dummy_data import populate_all
from utils.delete_all_data import delete_all_items
import uuid

app = FastAPI(title="ShopTown API")

@app.on_event("startup")
def startup_event():
    ensure_users_table_exists()
    ensure_products_table_exists()
    ensure_orders_table_exists()

@app.get("/")
def root():
    return {"message": "Welcome to ShopTown!"}

@app.post("/populate")
def populate():
    populate_all('utils/USER_MOCK_DATA.csv', 'utils/PRODUCT_MOCK_DATA.csv')
    return {"message": "Users, Products and Orders populated!"}

@app.delete("/delete-all")
def delete_all():
    delete_all_items('Products')
    delete_all_items('Users')
    delete_all_items('Orders')
    return {"message": "All products, users and orders deleted."}

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

@app.get("/users")
def list_users():
    table = get_users_table()
    response = table.scan()
    return {"users": response.get('Users', [])}

@app.post("/purchase/{product_id}")
def purchase(product_id: str, buyer_id: str = Query(...), bought_quantity: int = Query(1)):
    order = purchase_product(buyer_id, product_id, bought_quantity)
    return {"message": "Order was succesfull.", "order": order}

@app.get("/orders/{buyer_id}")
def list_orders_by_buyer(buyer_id: str):
    orders = get_orders_by_buyer(buyer_id)
    return {"orders": orders}

@app.get("/products/seller/{seller_id}")
def list_products_by_seller(seller_id: str):
    products = get_products_by_seller(seller_id)
    return {"products": products}

@app.get("/products/filtered") # asc ili desc za sort
def list_products_filtered(
    search: str = None,
    min_price: float = None,
    max_price: float = None,
    sort: str = "asc",
    page: int = 1,
    limit: int = 20
):
    table = get_products_table()

    response = table.scan()
    items = response.get('Items', [])

    if search:
        items = [
            item for item in items
            if search.lower() in item['name'].lower() or search.lower() in item['description'].lower()
        ]

    if min_price is not None:
        items = [item for item in items if float(item['price']) >= min_price]

    if max_price is not None:
        items = [item for item in items if float(item['price']) <= max_price]

    reverse = sort.lower() == "desc"
    items.sort(key=lambda x: float(x['price']), reverse=reverse)

    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]

    return {
        "page": page,
        "limit": limit,
        "total": len(items),
        "products": paginated_items
    }





