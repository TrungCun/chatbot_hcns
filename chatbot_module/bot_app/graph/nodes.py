import os
import json
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage

from bot_app.graph.state import AppState
from bot_app.prompt.loader import load_prompt
from bot_app.model.llm import llm
from bot_app.config import _REPO_ROOT

from bot_app.log import get_logger
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
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    logger.info(f"[classify_user_intent] CURRENT CONTEXT: '{context}'")
    
    file_urls = state.get("file_urls") or []
    
    # Chỉ khi nào có đính kèm file thì mới coi là provide
    intent = "provide" if file_urls else "ask"

    logger.info(f"[classify_user_intent] intent='{intent}'")
    return {"intent": intent}
