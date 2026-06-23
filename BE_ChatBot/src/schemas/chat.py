from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    conversationSessionId: str = "default"
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
