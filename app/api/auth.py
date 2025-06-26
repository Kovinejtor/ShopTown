from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.auth_service import register_user, authenticate_user

router = APIRouter(prefix="/auth")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(data: RegisterRequest):
    try:
        return register_user(data.username, data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(data: LoginRequest):
    token_data = authenticate_user(data.email, data.password)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token_data