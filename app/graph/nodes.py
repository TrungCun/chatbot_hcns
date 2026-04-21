"""
Nodes cho Parent Graph.
"""
from langchain_core.output_parsers import StrOutputParser

from app.graph.state import AppState
from app.prompt.loader import load_prompt
from app.log import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Node: classify_intent
# Entry point duy nhất của toàn hệ thống.
# Phân loại tin nhắn user → routing sang đúng subgraph.
# ---------------------------------------------------------------------------

async def classify_intent(state: AppState) -> dict:
    """Phân loại intent của tin nhắn → quyết định subgraph nào xử lý."""
    message = state["message"]
    logger.info(f"[classify_intent] message='{message}'")

    from app.model.llm import get_llm
    llm = get_llm(stream=False)
    chain = load_prompt("parent/classify_intent") | llm | StrOutputParser()

    result = await chain.ainvoke({"message": message})
    intent = result.strip().lower()

    # Fallback an toàn
    if intent not in ("ask", "provide"):
        intent = "ask"

    # Set response mặc định (placeholder)
    if intent == "ask":
        response = "[DRAFT] Bạn đang hỏi về công ty/vị trí. RAG pipeline chưa hoàn chỉnh."
    else:
        response = "[DRAFT] Bạn muốn cung cấp thông tin. Interview flow chưa hoàn chỉnh."

    logger.info(f"[classify_intent] intent='{intent}'")
    return {"intent": intent, "response": response}
