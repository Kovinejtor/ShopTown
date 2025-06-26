from app.core.databse import dynamodb

def ensure_users_table_exists():
    table_name = "Users"

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

def get_users_table():
    return dynamodb.Table('Users')