from fastapi import APIRouter, Depends

from src.api.deps import get_current_user
from src.models.user import User
from src.schemas.auth import AuthUserResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/firebase-login", response_model=AuthUserResponse)
def firebase_login(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me", response_model=AuthUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
