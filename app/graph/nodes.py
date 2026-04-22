from langchain_core.output_parsers import StrOutputParser

from app.graph.state import AppState
from app.prompt.loader import load_prompt
from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

async def classify_intent(state: AppState) -> dict:
    message = state["message"]
    logger.info(f"[classify_intent] message='{message}'")

    llm = get_llm(stream=False)
    chain = load_prompt("parent/classify_intent") | llm | StrOutputParser()

    result = await chain.ainvoke({"message": message})
    intent = result.strip().lower()

    # Fallback
    if intent not in ("ask", "provide"):
        intent = "ask"

    logger.info(f"[classify_intent] intent='{intent}'")

    return {"intent": intent}