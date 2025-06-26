from fastapi import FastAPI, Query, Depends, HTTPException
from app.models.product import Product, ProductCreate
from app.services.user_service import ensure_users_table_exists, get_users_table
from app.services.product_service import ensure_products_table_exists, get_products_table, get_products_by_seller
from app.services.order_service import ensure_orders_table_exists, purchase_product, get_orders_by_buyer, refund_order
from app.services.review_service import ensure_reviews_table_exists
from decimal import Decimal
from app.utils.fill_dummy_data import populate_all
from app.utils.delete_all_data import delete_all_items
import uuid
from app.api import auth
from app.core.dependecies import get_current_user
from app.models.user import User
from fastapi.security import HTTPBearer
from app.services.recommender_service import get_recommendations_for_user

security = HTTPBearer()

app = FastAPI(
    title="ShopTown API",
    swagger_ui_init_oauth={"usePkceWithAuthorizationCodeGrant": True}
)

app.include_router(auth.router)

@app.on_event("startup")
def startup_event():
    ensure_users_table_exists()
    ensure_products_table_exists()
    ensure_orders_table_exists()
    ensure_reviews_table_exists()

# --- Public endpoints ---

@app.get("/")
def root():
    return {"message": "Welcome to ShopTown!"}

@app.get("/products")
def list_products():
    table = get_products_table()
    response = table.scan()
    return {"products": response.get('Items', [])}

@app.get("/products/seller/{seller_id}")
def list_products_by_seller(seller_id: str):
    products = get_products_by_seller(seller_id)
    return {"products": products}

@app.get("/products/filtered")
def list_products_filtered(
    search: str = None, min_price: float = None, max_price: float = None,
    sort: str = "asc", page: int = 1, limit: int = 20
):
    table = get_products_table()
    response = table.scan()
    items = response.get('Items', [])
    if search:
        items = [item for item in items if search.lower() in item['name'].lower() or search.lower() in item['description'].lower()]
    if min_price is not None:
        items = [item for item in items if float(item['price']) >= min_price]
    if max_price is not None:
        items = [item for item in items if float(item['price']) <= max_price]
    reverse = sort.lower() == "desc"
    items.sort(key=lambda x: float(x['price']), reverse=reverse)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]
    return {"page": page, "limit": limit, "total": len(items), "products": paginated_items}

@app.get("/recommendations/{user_id}", dependencies=[Depends(security)])
def get_recommendations(user_id: str, current_user: User = Depends(get_current_user)):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to recommendations")
    recs = get_recommendations_for_user(user_id)
    return {"recommendations": recs}

# --- Protected Endpoints ---

@app.post("/populate", dependencies=[Depends(security)])
def populate(current_user: User = Depends(get_current_user)):
    populate_all('utils/USER_MOCK_DATA.csv', 'utils/PRODUCT_MOCK_DATA.csv')
    return {"message": "Users, Products and Orders populated!"}

@app.delete("/delete-all", dependencies=[Depends(security)])
def delete_all(current_user: User = Depends(get_current_user)):
    delete_all_items('Products')
    delete_all_items('Users')
    delete_all_items('Orders')
    return {"message": "All products, users and orders deleted."}

@app.get("/me", dependencies=[Depends(security)])
def read_profile(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "email": current_user.email, "username": current_user.username}

@app.post("/products", dependencies=[Depends(security)])
def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    table = get_products_table()
    item = product_data.dict()
    item['id'] = str(uuid.uuid4())
    item['price'] = Decimal(str(item['price']))
    item['seller_id'] = current_user.id
    table.put_item(Item=item)
    return {"message": "Product added!", "product": item}

@app.get("/users", dependencies=[Depends(security)])
def list_users(current_user: User = Depends(get_current_user)):
    table = get_users_table()
    response = table.scan()
    return {"users": response.get('Items', [])}

@app.post("/purchase/{product_id}", dependencies=[Depends(security)])
def purchase(product_id: str, bought_quantity: int = Query(1), current_user: User = Depends(get_current_user)):
    order = purchase_product(current_user.id, product_id, bought_quantity)
    return {"message": "Order was succesfull.", "order": order}

@app.get("/orders/{buyer_id}", dependencies=[Depends(security)])
def list_orders_by_buyer(buyer_id: str, current_user: User = Depends(get_current_user)):
    if buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to orders")
    orders = get_orders_by_buyer(buyer_id)
    return {"orders": orders}

@app.post("/refund/{order_id}", dependencies=[Depends(security)])
def refund(order_id: str, current_user: User = Depends(get_current_user)):
    if order_id.startswith(":"):
        order_id = order_id[1:]
    return refund_order(order_id)