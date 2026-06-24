from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.firebase import verify_firebase_id_token
from src.repositories.user_repository import UserRepository
from src.models.user import User


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def login_with_firebase_token(self, id_token: str) -> User:
        """
        1. Verify id token
        2. Extract in4 user tu token
        3. Find || Create user
        """
        try:
            # Verify
            decoded_token = verify_firebase_id_token(id_token)
        except Exception as exc:
            print(f"Firebase token verify failed: {type(exc).__name__}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token",
            ) from exc

        # Extract
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        full_name = decoded_token.get("name")
        avatar_url = decoded_token.get("picture")

        # Validate (uid + email required)
        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token missing required user info",
            )

        # Upsert user
        user = self.user_repository.get_by_firebase_uid(firebase_uid)
        # Chua co user => Tao moi
        if user is None:
            user = self.user_repository.create_firebase_user(
                firebase_uid=firebase_uid,
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
            )
        else:
            # Da co user => Cap nhat (in4 gg cua user co the thay doi)
            user = self.user_repository.update_firebase_profile(
                user=user,
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
            )

        self.db.commit()
        # self.db.refresh(user)

        return user
