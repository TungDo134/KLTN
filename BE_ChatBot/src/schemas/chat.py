from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    prompt: str
    conversationSessionId: str = "default"
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
