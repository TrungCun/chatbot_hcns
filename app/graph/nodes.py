import os
import json
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage

from app.graph.state import AppState
from app.prompt.loader import load_prompt
from app.model.llm import llm

from app.log import get_logger
logger = get_logger(__name__)

async def update_context(state: AppState) -> Dict[str, Any]:
    history = state.get("history", [])
    existing_context = state.get("context") or "Chưa có bối cảnh."

    if not history:
        return {}
    
    KEEP_COUNT = 8

    logger.info(f"[update_context] CONTEXT cũ: '{existing_context}'")
    logger.info(f"[update_context] Đang đọc {len(history)} tin nhắn trong history.")

    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        prompt = load_prompt("parent/update_context")
        chain = prompt | llm
        response = await chain.ainvoke({
            "n": 3,
            "existing_context": existing_context,
            "history": filtered_history,
            # Vì loader của bạn luôn chèn 1 block HumanMessage cuối cùng, 
            # ta dùng nó làm câu lệnh kích hoạt (Trigger) luôn cho sạch!
            "message": "Dựa vào bối cảnh cũ và lịch sử chat trên, hãy nhả ra bản cập nhật bối cảnh mới." 
        })
        new_context = response.content
        logger.info(f"[update_context] CONTEXT mới: '{new_context}'")
    except Exception as e:
        logger.error(f"[update_context] Lỗi khi gọi LLM: {e}")
        new_context = existing_context
    
    delete_messages = []
    # Nếu tổng số tin nhắn hiện tại vượt mức cho phép
    if len(history) > KEEP_COUNT:
        # Xác định những tin nhắn cũ cần bị loại bỏ (tất cả các tin nằm trước phần KEEP_COUNT)
        messages_to_delete = history[:-KEEP_COUNT]
        
        # Dùng RemoveMessage của LangGraph để đánh dấu xóa dựa trên ID
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_delete if m.id]
        logger.info(f"[update_context] Đã dọn {len(delete_messages)} tin nhắn cũ khỏi history.")

    # Chốt State: Trả về bối cảnh mới và danh sách lệnh xóa tin nhắn
    return {
        "context": new_context,
        "history": delete_messages # Reducer add_messages sẽ nhận danh sách RemoveMessage này và tự xóa
    }

async def classify_user_intent(state: AppState) -> dict:
    message = state["message"]
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    file_urls = state.get("file_urls") or []
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]
    
    try:
        prompt = load_prompt("parent/classify_intent")
        chain = prompt | llm
        response = await chain.ainvoke({
                "message": message,
                "context": context,
                "history": filtered_history
            })
        intent = response.content.strip().lower()
    except Exception as e:
        logger.error(f"[classify_user_intent] LLM Error: {e}")
        intent = "provide" if file_urls else "ask" # Fallback thông minh: có ảnh thì thường là cung cấp CV

    # Fallback
    if intent not in ("ask", "provide"):
        intent = "ask"

    logger.info(f"[classify_user_intent] intent='{intent}'")
    return {"intent": intent}


async def save_history(state: AppState) -> Dict[str, Any]:
    """
    Node lưu lại lịch sử chat vào folder history/user_id/session_id.json
    """
    user_id = state.get("user_id", "default_user")
    session_id = state.get("session_id", "unknown_session")
    history = state.get("history", [])
    file_urls = state.get("file_urls", [])

    # Chuẩn bị dữ liệu để lưu
    messages_data = []
    for msg in history:
        role = "user" if isinstance(msg, HumanMessage) else "assistant" if isinstance(msg, AIMessage) else "other"
        # Bỏ qua các tin nhắn meta như RemoveMessage
        if role != "other":
            messages_data.append({
                "role": role,
                "content": str(msg.content)
            })

    save_data = {
        "session_id": session_id,
        "messages": messages_data,
        "file_urls": file_urls,
        "updated_at": datetime.now().isoformat(),
        "message_count": len(messages_data)
    }

    # Tạo thư mục và lưu file
    dir_path = os.path.join("history", user_id)
    os.makedirs(dir_path, exist_ok=True)
    
    file_path = os.path.join(dir_path, f"{session_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        logger.info(f"[save_history] Saved history to {file_path}")
    except Exception as e:
        logger.error(f"[save_history] Error saving history: {e}")

    return {}