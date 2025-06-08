from core.databse import dynamodb

def get_table(table_name):
    return dynamodb.Table(table_name)

def delete_all_items(table_name):
    table = get_table(table_name)
    response = table.scan()
    items = response.get('Items', [])

    print(f"Deleting {len(items)} items from {table_name}...")

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'id': item['id']
                }
            )
    print(f"All items from {table_name} are deleted.")