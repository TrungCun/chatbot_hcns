from typing import Optional, List
from pydantic import BaseModel, Field

class FilePayload(BaseModel):
    filename: str
    content_type: str
    content: bytes

class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_info: Optional[str] = None
    job_context: Optional[str] = None
    message: Optional[str] = None
    files: List[FilePayload] = Field(default_factory=list)

class ChatResponse(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    response: Optional[str]
