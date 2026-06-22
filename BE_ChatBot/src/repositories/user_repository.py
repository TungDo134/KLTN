from sqlalchemy.orm import Session

from src.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    # Tim user theo id
    def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.firebase_uid == firebase_uid, User.deleted_at.is_(None))
            .first()
        )

    # Tao user (FIREBASE)
    def create_firebase_user(
        self,
        firebase_uid: str,
        email: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> User:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            provider="google",
        )
        self.db.add(user)
        self.db.flush()  # ghi xuong db chua commit (transaction - service layer lo)
        self.db.refresh(user)  # dong bo value from db tu sinh ra vao object Python

        return user

    # Update user (FIREBASE)
    def update_firebase_profile(
        self,
        user: User,
        email: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> User:
        user.email = email
        user.full_name = full_name
        user.avatar_url = avatar_url
        user.provider = "google"

        self.db.flush()  # ghi xuong db chua commit (transaction - service layer lo)
        self.db.refresh(user)

        return user
