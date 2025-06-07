from core.databse import dynamodb
from botocore.exceptions import ClientError

def create_products_table():
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
        print(f"Tablica {table_name} kreirana.")
    else:
        print(f"Tablica {table_name} već postoji.")

def get_products_table():
    return dynamodb.Table('Products')