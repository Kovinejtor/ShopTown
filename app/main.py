from fastapi import FastAPI, Query, Depends, HTTPException
from app.models.product import Product, ProductCreate
from app.services.user_service import ensure_users_table_exists, get_users_table
from app.services.product_service import ensure_products_table_exists, get_products_table, get_products_by_seller
from app.services.order_service import ensure_orders_table_exists, purchase_product, get_orders_by_buyer, refund_order, get_orders_table
from app.services.review_service import ensure_reviews_table_exists, get_reviews_table, create_review
from decimal import Decimal
from app.utils.fill_dummy_data import populate_all
from app.utils.delete_all_data import delete_all_items
import uuid
from app.api import auth
from app.core.dependecies import get_current_user
from app.models.user import User
from fastapi.security import HTTPBearer
from app.services.collaborative_recommender_service import get_collaborative_based_recommendations
from app.services.content_recommender_service import get_content_based_recommendations
from app.services.gradient_boost_recommender_service import get_gb_recommendations, train_gradient_boost_model
from boto3.dynamodb.conditions import Key
from app.models.review import Review
import re

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

@app.get("/")
def root():
    return {"message": "Welcome to ShopTown!"}

@app.post("/populate")
def populate():
    populate_all('app/utils/USER_MOCK_DATA.csv', 'app/utils/PRODUCT_MOCK_DATA.csv')
    return {"message": "Users, Products, Orders and Reviews populated!"}

@app.delete("/delete-all")
def delete_all():
    delete_all_items('Products')
    delete_all_items('Users')
    delete_all_items('Orders')
    delete_all_items('Reviews')
    return {"message": "All products, users,reviews and orders deleted."}

# --- Other public endpoints ---
@app.get("/products")
def list_products():
    table = get_products_table()
    response = table.scan()
    return {"products": response.get('Items', [])}

@app.get("/products/search")
def search_products(keyword: str):
    table = get_products_table()
    response = table.scan()
    items = response.get('Items', [])

    def word_match(text: str, keyword: str):
        return keyword.lower() in text.lower().split()

    matched = [
        item for item in items
        if word_match(item['name'], keyword) or word_match(item['description'], keyword)
    ]

    return {"products": matched}

@app.get("/products/filtered")
def list_products_filtered(
    search: str = None, min_price: float = None, max_price: float = None,
    sort: str = "asc", page: int = 1, limit: int = 20
):
    table = get_products_table()
    response = table.scan()
    items = response.get('Items', [])

    def word_match(text: str, keyword: str):
        words = re.findall(r'\b\w+\b', text.lower())
        return keyword.lower() in words

    if search:
        items = [
            item for item in items
            if word_match(item['name'], search) or word_match(item['description'], search)
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

@app.get("/products/low-stock", dependencies=[Depends(security)])
def list_low_stock_products(threshold: int = 5, current_user: User = Depends(get_current_user)):
    table = get_products_table()
    response = table.scan()
    items = response.get('Items', [])
    low_stock = [item for item in items if int(item['stock']) <= threshold]
    return {"products": low_stock}

@app.get("/products/{product_id}")
def get_product_by_id(product_id: str):
    table = get_products_table()
    response = table.get_item(Key={'id': product_id})
    item = response.get('Item')
    if not item:
        raise HTTPException(status_code=404, detail="Product not found.")
    return item

@app.get("/products/seller/{seller_id}")
def list_products_by_seller(seller_id: str):
    products = get_products_by_seller(seller_id)
    return {"products": products}

@app.get("/reviews/user/{user_id}")
def list_reviews_by_user(user_id: str):
    table = get_reviews_table()
    response = table.scan(FilterExpression=Key('user_id').eq(user_id))
    return {"reviews": response.get('Items', [])}

@app.get("/reviews/{review_id}")
def get_review_by_id(review_id: str):
    table = get_reviews_table()
    response = table.get_item(Key={'review_id': review_id})
    item = response.get('Item')
    
    if not item:
        raise HTTPException(status_code=404, detail="Review not found.")
    
    return {"review": item}

@app.get("/reviews/product/{product_id}")
def get_reviews_for_product(product_id: str):
    products_table = get_products_table()
    reviews_table = get_reviews_table()

    # Get product to access review_ids
    product_response = products_table.get_item(Key={'id': product_id})
    product = product_response.get("Item")

    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    review_ids = product.get("review_ids", [])

    if not review_ids:
        return {"reviews": []}

    reviews = []
    for rid in review_ids:
        review_response = reviews_table.get_item(Key={'review_id': rid})
        review = review_response.get("Item")
        if review:
            reviews.append(review)

    return {"reviews": reviews}

@app.get("/recommendations/collaborative/{user_id}")
def get_collaborative_recommendations(user_id: str):
    recs = get_collaborative_based_recommendations(user_id)
    return {"recommendations": recs}

@app.get("/recommendations/content/{user_id}")
def get_content_recommendations(user_id: str):
    recs = get_content_based_recommendations(user_id)
    return {"recommendations": recs}

@app.post("/recommendations/gradientboost/train")
def train_gb_model():
    model = train_gradient_boost_model()
    if model is None:
        return {"message": "Not enough data to train model."}
    return {"message": "Model trained and saved."}

@app.get("/recommendations/gradientboost/{user_id}")
def get_gb_recommendations_route(user_id: str):
    recs = get_gb_recommendations(user_id)
    return {"recommendations": recs}

'''
For example! I removed the option to check that the user id needs to be the same as the one checked so i could test better. On the "/orders/{buyer_id}" is shown
@app.get("/recommendations/{user_id}", dependencies=[Depends(security)])
def get_recommendations(user_id: str, current_user: User = Depends(get_current_user)):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to recommendations")
    recs = get_recommendations_for_user(user_id)
    return {"recommendations": recs}
'''

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

@app.post("/reviews", dependencies=[Depends(security)])
def create_review_route(review: Review, current_user: User = Depends(get_current_user)):
    create_review(review)
    return {"message": "Review created."}

@app.get("/users", dependencies=[Depends(security)])
def list_users(current_user: User = Depends(get_current_user)):
    table = get_users_table()
    response = table.scan()
    return {"users": response.get('Items', [])}

@app.post("/purchase/{product_id}", dependencies=[Depends(security)])
def purchase(product_id: str, bought_quantity: int = Query(1), current_user: User = Depends(get_current_user)):
    order = purchase_product(current_user.id, product_id, bought_quantity)
    return {"message": "Order was succesfull.", "order": order}

@app.get("/orders", dependencies=[Depends(security)])
def list_all_orders(current_user: User = Depends(get_current_user)):
    table = get_orders_table()
    response = table.scan()
    return {"orders": response.get('Items', [])}

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

