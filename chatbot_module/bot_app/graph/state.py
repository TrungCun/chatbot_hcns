from typing import Dict, Literal, Optional, List, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
import re

from bot_app.schema.summary_schema import CVTemplate

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


def extract_info_from_userinfo(user_info: str):
    if not user_info:
        return None, None, None
    # Pattern: Tên (có thể chứa _) + "_" + SĐT (số, dấu +, dấu _) + "_" + Email (chứa @)
    match = re.match(r'^(.*?)_([+0-9_]{4,20})_(.*@.*)$', user_info)
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
    user_info: Optional[str] = None,
    job_context: Optional[str] = None,
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
        initial_cv = CVTemplate()
        if job_context and not session_id.endswith("_000000"):
            match = re.search(r"Vị trí:\s*(.*)", job_context)
            if match:
                initial_cv.candidate_overview.applied_position = match.group(1).strip()
        base_template = initial_cv.model_dump()

    initial_context = None
    if not previous_state:
        context_parts = []
        if user_info:
            name, phone, email = extract_info_from_userinfo(user_info)
            if name and phone and email:
                context_parts.append(f"Thông tin ứng viên: Tên {name}, SĐT {phone}, Email {email}.")
        if job_context and not session_id.endswith("_000000"):
            context_parts.append(f"Vị trí ứng tuyển hiện tại:\n{job_context}")

        if context_parts:
            initial_context = "\n\n".join(context_parts)

    old_file_urls = previous_state.get("file_urls", []) if previous_state else []
    current_file_urls = file_urls or []
    
    combined_file_urls = []
    for url in old_file_urls + current_file_urls:
        if url not in combined_file_urls:
            combined_file_urls.append(url)

    return {
        "user_id": user_id,
        "session_id": session_id,
        "message": message,
        "file_urls": combined_file_urls,
        "history": [HumanMessage(content=message)],
        "error": None,
        "context": previous_state.get("context") if previous_state else initial_context,
        "intent": previous_state.get("intent", "ask") if previous_state else "ask",
        "template": base_template,
        "summary_status": previous_state.get("summary_status", "collecting") if previous_state else "collecting",
        "response": None  # Luôn reset response cho lượt chat mới
    }
