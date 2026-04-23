from langchain_core.output_parsers import StrOutputParser

from app.graph.state import AppState
from app.prompt.loader import load_prompt
from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

async def classify_user_intent(state: AppState) -> dict:
    """Level 1 Classification: Determine if user is asking or providing information.
    Returns: intent = 'ask' | 'provide'
    """
    message = state["message"]
    logger.info(f"[classify_user_intent] message='{message}'")

    llm = get_llm(stream=False)
    chain = load_prompt("parent/classify_intent") | llm | StrOutputParser()

    result = await chain.ainvoke({"message": message})
    intent = result.strip().lower()

    # Fallback
    if intent not in ("ask", "provide"):
        intent = "ask"

    logger.info(f"[classify_user_intent] intent='{intent}'")

    return {"intent": intent}