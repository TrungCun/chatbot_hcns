from typing import Dict, Literal, Optional, List, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

from app.schema.summary_schema import CVTemplate

class AppState(TypedDict):
    user_id: str
    session_id: str
    message: str
    history: Annotated[List[BaseMessage], add_messages]
    error: Optional[str]
    context: Optional[str] # tóm tắt đoạn chat

    intent: Literal["ask", "provide"]

    template: Dict[str, Any]
    response: Optional[str]
    
    # Danh sách URL/Path của các file đã lưu (để ghi history)
    file_urls: Optional[List[str]]


def create_initial_state(
    message: str,
    session_id: str,
    user_id: str = "default_user",
    file_urls: Optional[List[str]] = None,
    previous_state: Optional[Dict[str, Any]] = None
) -> AppState:
    """
    Khởi tạo AppState. 
    Đảm bảo các giá trị mặc định luôn nhất quán.
    """
    if previous_state and previous_state.get("template"):
        base_template = previous_state.get("template")
    else:
        base_template = CVTemplate().model_dump()
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "message": message,
        "file_urls": file_urls or [],
        "history": [HumanMessage(content=message)], 
        "error": None,
        "context": previous_state.get("context") if previous_state else None,
        "intent": previous_state.get("intent", "ask") if previous_state else "ask",
        "template": base_template, 
        "response": None  # Luôn reset response cho lượt chat mới
    }