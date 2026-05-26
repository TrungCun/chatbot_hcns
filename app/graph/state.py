from typing import Dict, Literal, Optional, List, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
import re

from app.schema.summary_schema import CVTemplate

class AppState(TypedDict):
    user_id: str
    session_id: str
    message: str
    # Danh sách URL/Path của các file đã lưu 
    file_urls: Optional[List[str]]
    history: Annotated[List[BaseMessage], add_messages]

    error: Optional[str]
    context: Optional[str] # tóm tắt đoạn chat

    intent: Literal["ask", "provide"]

    current: Optional[str] # vị trí hiện tại uv đang quan tâm theo danh sách vị trí đang tuyển. 
    template: Dict[str, Any]
    summary_status: Literal["collecting", "pending_confirmation", "confirmed"]
    response: Optional[str]


def extract_info_from_userid(user_id: str):
    # Pattern: Tên (có thể chứa _) + "_" + SĐT (số, dấu +, dấu _) + "_" + Email (chứa @)
    match = re.match(r'^(.*?)_([+0-9_]{4,20})_(.*@.*)$', user_id)
    if match:
        name = match.group(1).replace("_", " ")
        phone = match.group(2).replace("_", " ")
        email = match.group(3)
        return name, phone, email
    return None, None, None

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
        
    initial_context = None
    if not previous_state and user_id != "default_user":
        name, phone, email = extract_info_from_userid(user_id)
        if name and phone and email:
            initial_context = f"Thông tin ứng viên: Tên {name}, SĐT {phone}, Email {email}."
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "message": message,
        "file_urls": file_urls or [],
        "history": [HumanMessage(content=message)], 
        "error": None,
        "context": previous_state.get("context") if previous_state else initial_context,
        "intent": previous_state.get("intent", "ask") if previous_state else "ask",
        "template": base_template,
        "summary_status": previous_state.get("summary_status", "collecting") if previous_state else "collecting",
        "response": None  # Luôn reset response cho lượt chat mới
    }