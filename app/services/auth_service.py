from models.user import User
from core.databse import dynamodb
from core.security import hash_password, verify_password, create_access_token
import uuid

def get_users_table():
    return dynamodb.Table('Users')

def register_user(username: str, email: str, password: str):
    table = get_users_table()

    response = table.scan(
        FilterExpression="email = :e",
        ExpressionAttributeValues={":e": email}
    )
    if response["Items"]:
        raise ValueError("User with this email already exists.")

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password=hash_password(password)
    )
    table.put_item(Item=user.dict())
    return {"message": "User registered successfully."}

def authenticate_user(email: str, password: str):
    table = get_users_table()

    response = table.scan(
        FilterExpression="email = :e",
        ExpressionAttributeValues={":e": email}
    )
    users = response.get("Items", [])
    if not users:
        return None

    user = users[0]
    if not verify_password(password, user['password']):
        return None

    token = create_access_token({"sub": user['id'], "email": user['email']})
    return {"access_token": token, "token_type": "bearer"}