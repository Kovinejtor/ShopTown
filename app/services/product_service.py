from core.databse import dynamodb
from boto3.dynamodb.conditions import Key
from models.product import Product
from decimal import Decimal

def ensure_products_table_exists():
    table_name = "Products"

    existing_tables = dynamodb.meta.client.list_tables()["TableNames"]
    if table_name not in existing_tables:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH' 
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"Table {table_name} created.")
    else:
        print(f"Table {table_name} already exists.")

def get_products_table():
    return dynamodb.Table('Products')

def get_products_by_seller(seller_id):
    table = get_products_table()
    response = table.scan(FilterExpression=Key('seller_id').eq(seller_id))
    items = response.get('Items', [])
    return [Product(**item) for item in items]