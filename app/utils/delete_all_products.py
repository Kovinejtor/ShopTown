from core.databse import dynamodb

def get_products_table():
    return dynamodb.Table('Products')

def delete_all_products():
    table = get_products_table()
    response = table.scan()
    items = response.get('Items', [])

    print(f"Brisanje {len(items)} proizvoda...")

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'id': item['id'] 
                }
            )