import uuid
from datetime import datetime
from decimal import Decimal
from app.core.databse import dynamodb
from boto3.dynamodb.conditions import Key
from fastapi import HTTPException
from dateutil import parser
from app.models.order import Order
from app.models.product import Product
from datetime import timezone

def ensure_orders_table_exists():
    existing_tables = dynamodb.meta.client.list_tables()["TableNames"]
    if 'Orders' not in existing_tables:
        dynamodb.create_table(
            TableName='Orders',
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}  
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Table Orders created.")
    else:
        print("Table Orders already exists.")

def get_orders_table():
    return dynamodb.Table('Orders')

def get_products_table():
    return dynamodb.Table('Products')

def purchase_product(buyer_id, product_id, bought_quantity):
    products_table = get_products_table()
    orders_table = get_orders_table()

    product = products_table.get_item(Key={'id': product_id}).get('Item')

    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    current_stock = product['stock']
    if current_stock <= 0:
        raise HTTPException(status_code=400, detail="Product is not in storage.")
    
    if bought_quantity > current_stock:
        raise HTTPException(
            status_code=400,
            detail=f"You cannot buy this product in {bought_quantity} quantity. In storage there is just {current_stock} ."
        )

    new_stock = current_stock - bought_quantity

    if new_stock == 0:
        products_table.delete_item(Key={'id': product_id})
    else:
        products_table.update_item(
            Key={'id': product_id},
            UpdateExpression="SET stock = :stock",
            ExpressionAttributeValues={':stock': new_stock}
        )

    product_price = Decimal(product['price']) 
    total_price = product_price * bought_quantity

    order = Order(
        id=str(uuid.uuid4()),
        buyer_id=buyer_id,
        product_id=product_id,
        product_name=product['name'],
        product_price=product_price,
        description=product['description'],
        purchase_date=datetime.utcnow().isoformat() + "Z",
        quantity=bought_quantity,
        total_price=total_price,
        seller_id=product['seller_id'],
        status="completed"
    ).dict()

    orders_table.put_item(Item=order)

    return order


def get_orders_by_buyer(buyer_id):
    table = get_orders_table()

    response = table.scan(
        FilterExpression=Key('buyer_id').eq(buyer_id)
    )
    return response.get('Items', [])

def refund_order(order_id: str):
    orders_table = get_orders_table()
    products_table = get_products_table()

    order_response = orders_table.get_item(Key={'id': order_id})
    order = order_response.get('Item')

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order['status'] == 'refunded':
        raise HTTPException(status_code=400, detail="Order already refunded.")

    now = datetime.now(timezone.utc)
    purchase_date = parser.isoparse(order['purchase_date'])
    if (now - purchase_date).days > 14:
        raise HTTPException(status_code=400, detail="Refund period has expired.")

    product_response = products_table.get_item(Key={'id': order['product_id']})
    product = product_response.get('Item')

    if product:
        new_stock = product['stock'] + order['quantity']
        products_table.update_item(
            Key={'id': order['product_id']},
            UpdateExpression="SET stock = :stock",
            ExpressionAttributeValues={':stock': new_stock}
        )
    else:
        recreated_product = Product(
            id=order['product_id'],
            name=order['product_name'],
            description=order.get('description', ''),
            price=Decimal(str(order['product_price'])),
            stock=order['quantity'],
            seller_id=order['seller_id']
        )
        products_table.put_item(Item=recreated_product.dict())

    orders_table.update_item(
        Key={'id': order_id},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": "refunded"}
    )

    return {"message": "Refund processed successfully."}