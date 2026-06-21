from pydantic import BaseModel, ConfigDict


class AuthUserResponse(BaseModel):
    id: str
    firebase_uid: str | None
    email: str
    full_name: str | None
    avatar_url: str | None
    provider: str
    status: str

    model_config = ConfigDict(from_attributes=True)
