from app.core.databse import dynamodb
from app.models.review import Review
from boto3.dynamodb.conditions import Key
from decimal import Decimal

def ensure_reviews_table_exists():
    table_name = "Reviews"

    existing_tables = dynamodb.meta.client.list_tables()["TableNames"]
    if table_name not in existing_tables:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'review_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'review_id', 'AttributeType': 'S'},
                {'AttributeName': 'product_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'product_index',
                    'KeySchema': [
                        {'AttributeName': 'product_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Reviews table created.")
    else:
        print("Reviews table already exists.")

def get_reviews_table():
    return dynamodb.Table("Reviews")

def get_reviews_by_product(product_id: str):
    table = get_reviews_table()
    response = table.query(
        IndexName='product_index',
        KeyConditionExpression=Key('product_id').eq(product_id)
    )
    return response.get('Items', [])

def create_review(review_data: Review):
    table = get_reviews_table()
    table.put_item(Item=review_data.dict())