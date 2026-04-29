"""
Pydantic schemas cho API chat và job positions.
"""
from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class Attachment(BaseModel):
    """
    Schema cho các file đính kèm (ảnh hoặc tài liệu).
    """
    filename: str = Field(..., description="Tên file")
    content_type: str = Field(..., description="MIME type của file (vd: image/png, application/pdf)")
    content: str = Field(..., description="Nội dung file dưới dạng base64 string")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=100000, description="Tin nhắn từ user")
    attachments: Optional[List[Attachment]] = Field(
        default=None,
        description="Danh sách các file đính kèm (ảnh hoặc tài liệu)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="ID session để maintain conversation state. Nếu None, server tạo UUID mới"
    )


class ChatResponse(BaseModel):
    """
    Response schema cho /chat endpoint.

    Fields:
        response: Câu trả lời từ chatbot (sinh từ LLM).
        intent: Intent được classify (ask | provide).
        session_id: ID session để client dùng cho turn tiếp theo.
        current_phase: Phase hiện tại (conversation | interview).
    """
    response: str = Field(..., description="Câu trả lời từ chatbot")
    intent: Literal["ask", "provide"] = Field(..., description="Intent của user message")
    session_id: str = Field(..., description="ID session cho turn tiếp theo")
    current_phase: Literal["conversation", "interview"] = Field(
        ...,
        description="Phase hiện tại: conversation (RAG Q&A) | interview (thu thập thông tin)"
    )

class FilePayload(BaseModel):
    """Cấu trúc file độc lập, không phụ thuộc FastAPI"""
    filename: str
    content_type: str
    content: bytes  # Dữ liệu nhị phân thô

class ChatServiceRequest(BaseModel):
    """Dữ liệu chuẩn chỉ gửi xuống Service"""
    message: Optional[str]
    session_id: Optional[str]
    files: List[FilePayload] = []