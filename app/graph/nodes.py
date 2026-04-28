from langchain_core.output_parsers import StrOutputParser

from app.graph.state import AppState
from app.prompt.loader import load_prompt
from app.model.llm import llm
from app.tools.multimodal import get_multimodal_messages

from app.log import get_logger
logger = get_logger(__name__)

async def classify_user_intent(state: AppState) -> dict:
    message = state["message"]
    attachments = state.get("attachments")
    logger.info(f"[classify_user_intent] message='{message[:50]}...', attachments={len(attachments) if attachments else 0}")

    prompt = load_prompt("parent/classify_intent")

    # 1. Format prompt với message text
    formatted_prompt = prompt.format(message=message)

    # 2. Tạo multimodal message nếu có ảnh
    messages = get_multimodal_messages(formatted_prompt, attachments)

    logger.info(f"[classify_user_intent] sending {len(messages)} messages to LLM (multimodal={bool(attachments)})")

    try:
        # Gọi LLM với timeout để tránh treo hệ thống
        response = await llm.ainvoke(messages, config={"timeout": 60000})
        intent = response.content.strip().lower()
    except Exception as e:
        logger.error(f"[classify_user_intent] LLM Error: {e}")
        intent = "provide" if attachments else "ask" # Fallback thông minh: có ảnh thì thường là cung cấp CV

    # Fallback
    if intent not in ("ask", "provide"):
        intent = "ask"

    logger.info(f"[classify_user_intent] intent='{intent}'")
    return {"intent": intent}