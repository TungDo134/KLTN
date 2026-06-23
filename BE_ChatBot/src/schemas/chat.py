from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    conversationSessionId: str = "default"


class ChatResponse(BaseModel):
    response: str
