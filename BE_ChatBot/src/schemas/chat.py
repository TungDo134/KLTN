from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    prompt: str
    conversationSessionId: str = "default"
    conversation_id: str | None = None
    retrieval_vector_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    recommendation_content_weight: float = Field(default=0.6, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    response: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
