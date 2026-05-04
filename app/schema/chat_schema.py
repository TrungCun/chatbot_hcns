from typing import Literal, Optional, List
from pydantic import BaseModel

class Attachment(BaseModel):
    filename: str
    content_type: str
    content: str

class FilePayload(BaseModel):
    filename: str
    content_type: str
    content: bytes

class ChatRequest(BaseModel):
    session_id: Optional[str]
    message: Optional[str]
    files: List[FilePayload] = []

class ChatResponse(BaseModel):
    session_id: str
    intent: Literal["ask", "provide"]
    response: str