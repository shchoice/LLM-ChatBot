from typing import List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    message: List[Message]
    max_tokens: int = 128
    temperature: float = 0.2
