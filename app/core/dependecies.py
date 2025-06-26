from fastapi import Depends, HTTPException, status
from app.core.security import decode_token
from app.models.user import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.user_service import get_users_table

bearer_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload["sub"]
    table = get_users_table()
    response = table.get_item(Key={'id': user_id})
    
    user = response.get('Item')
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    return User(**user)