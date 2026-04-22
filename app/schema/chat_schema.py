"""
Pydantic schemas cho API chat và job positions.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """
    Request schema cho /chat endpoint.

    Fields:
        message: Tin nhắn từ user.
        session_id: ID session để lưu state qua multiple turns.
                   Nếu không có → server tạo UUID mới.
    """
    message: str = Field(..., min_length=1, max_length=2000, description="Tin nhắn từ user")
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


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("ok", description="Status của server")
    version: str = Field("1.0.0", description="Version của API")

