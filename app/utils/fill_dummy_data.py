import csv
import uuid
from decimal import Decimal
from core.databse import dynamodb

def get_products_table():
    return dynamodb.Table('Products')

def populate_products_from_csv(csv_path):
    table = get_products_table()
    csv_path = 'utils/MOCK_DATA.csv'

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            product = {
                'id': str(uuid.uuid4()),  
                'name': row['product_name'],
                'price': Decimal(row['product_price']),
                'description': row['product_description'],
                'stock': int(row['product_quantity'])
            }
            table.put_item(Item=product)
            count += 1
