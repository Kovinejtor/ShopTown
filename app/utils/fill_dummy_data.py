import csv
import uuid
from decimal import Decimal
from app.core.databse import dynamodb
import random
from datetime import datetime, timedelta
from app.models.product import Product
from app.models.user import User
from app.models.order import Order
from app.models.review import Review
from app.services.review_service import ensure_reviews_table_exists, create_review

def ensure_table_exists(table_name, key_schema, attribute_definitions):
    existing_tables = dynamodb.meta.client.list_tables()["TableNames"]
    if table_name not in existing_tables:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"Table {table_name} created.")
    else:
        print(f"Table {table_name} already exists.")

def get_table(table_name):
    return dynamodb.Table(table_name)

def populate_users_from_csv(csv_path):
    ensure_table_exists(
        table_name='Users',
        key_schema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        attribute_definitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
    )
    table = get_table('Users')

    users = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                username=row['user'],   
                email=row['email'],
                password=row['password']
            )
            table.put_item(Item=user.dict())
            users.append(user_id) 
            count += 1
    print(f"Succesfully adde {count} users.")
    return users

def load_reviews(review_csv_path):
    with open(review_csv_path, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.DictReader(csvfile))
        random.shuffle(reader) 
        return reader

def populate_products_from_csv(csv_path, user_ids, review_csv_path):
    reviews_pool = load_reviews(review_csv_path)

    ensure_table_exists(
        table_name='Products',
        key_schema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        attribute_definitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
    )

    ensure_reviews_table_exists()

    product_table = get_table('Products')

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0

        for row in reader:
            product_id = str(uuid.uuid4())
            review_ids = []

            num_reviews = random.choices([0, 1, 2, 3], weights=[0.4, 0.3, 0.2, 0.1])[0]

            for _ in range(num_reviews):
                if not reviews_pool:
                    break
                review_data = reviews_pool.pop()

                review = Review(
                    review_id=str(uuid.uuid4()),
                    product_id=product_id,
                    user_id=random.choice(user_ids),
                    rating=Decimal(review_data['rating']),
                    review=review_data['review']
                )
                create_review(review)
                review_ids.append(review.review_id)

            product = Product(
                id=product_id,
                name=row['product_name'],
                price=Decimal(row['product_price']),
                description=row['product_description'],
                stock=int(row['product_quantity']),
                seller_id=random.choice(user_ids),
                review_ids=review_ids
            )

            product_table.put_item(Item=product.dict())
            count += 1

    print(f"Successfully added {count} products with reviews.")


def populate_mock_orders(n=500):
    dynamodb_resource = dynamodb

    products_table = dynamodb_resource.Table('Products')
    users_table = dynamodb_resource.Table('Users')
    orders_table = dynamodb_resource.Table('Orders')

    products_response = products_table.scan()
    products = products_response.get('Items', [])

    users_response = users_table.scan()
    users = users_response.get('Items', [])

    if not products or not users:
        print("There are no users or products to fill the orders.")
        return

    def random_date():
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 6, 30)
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return (start_date + timedelta(days=random_days)).isoformat() + "Z"

    for _ in range(n):
        product = random.choice(products)
        buyer = random.choice(users)
        quantity = random.randint(1, 5)
        product_price = Decimal(product['price'])
        total_price = product_price * quantity

        maybe_review = random.choice([True, False])
        review_id = None

        if maybe_review:
            review = Review(
                review_id=str(uuid.uuid4()),
                product_id=product['id'],
                user_id=buyer['id'],
                rating=Decimal(str(round(random.uniform(1, 5), 1))),
                review=random.choice([
                    "Great purchase!", "Satisfied with the product.", "Would not recommend.", 
                    "Exceeded expectations.", "Not what I hoped for."
                ])
            )
            create_review(review)
            review_id = review.review_id

        order = Order(
            id=str(uuid.uuid4()),
            buyer_id=buyer['id'],
            product_id=product['id'],
            product_name=product['name'],
            product_price=Decimal(str(product['price'])),
            description=product.get('description', ''),
            purchase_date=random_date(),
            quantity=quantity,
            total_price=product_price * quantity,
            seller_id=product['seller_id'],
            status="completed",
            review_id=review_id  
        )

        orders_table.put_item(Item=order.dict())

    print(f"Succesfully added {n} orders.")

def populate_all(users_csv_path, products_csv_path, review_csv_path='utils/REVIEW_DATA.csv'):
    user_ids = populate_users_from_csv(users_csv_path)
    populate_products_from_csv(products_csv_path, user_ids, review_csv_path)
    populate_mock_orders(500)
