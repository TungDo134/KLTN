from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials

from src.core.config import settings


# Lấy setting firebase
def _resolve_credentials_path() -> Path:
    # firebase-service-account.json
    if not settings.firebase_credentials_path:
        raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not configured")

    path = Path(settings.firebase_credentials_path)
    if path.is_absolute():
        print(f"Path is absolute: {path}")
        return path
    project_root = Path(__file__).resolve().parents[2]
    print(f"ROOT PATH: {project_root / path}")
    return project_root / path


def get_firebase_app():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    credentials_path = _resolve_credentials_path()

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Firebase credentials file not found: {credentials_path}"
        )

    cred = credentials.Certificate(str(credentials_path))
    return firebase_admin.initialize_app(cred)


def verify_firebase_id_token(id_token: str) -> dict:
    get_firebase_app()  # dam bao app da khoi tao
    # Trả về dict - JWT cua firebase: { uid, email, name, picture, iss, aud, exp, iat, ... }
    return auth.verify_id_token(id_token)
