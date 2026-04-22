from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.graph.conversation.state import ConversationState
from app.prompt.loader import load_prompt
from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

def _make_llm() -> ChatOpenAI:
    return get_llm(stream=False)


def _parse_lines(text: str) -> List[str]:
    return [line.strip() for line in text.strip().splitlines() if line.strip()]

async def analyze_query(state: ConversationState) -> dict:
    logger.info(f"[analyze_query] question='{state['message']}'")
    llm = _make_llm()
    chain = load_prompt("conversation/analyze_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    query_type = result.strip().lower()

    # Fallback
    if query_type not in ("simple", "complex", "factual"):
        query_type = "simple"

    logger.info(f"[analyze_query] query_type='{query_type}'")
    return {"query_type": query_type}


async def rewrite_query(state: ConversationState) -> dict:
    logger.info("[rewrite_query] rewriting simple query")
    llm = _make_llm()
    chain = load_prompt("conversation/rewrite_query") | llm | StrOutputParser()
    rewritten = await chain.ainvoke({"question": state["message"]})
    rewritten = rewritten.strip()
    logger.info(f"[rewrite_query] result='{rewritten}'")
    return {"rewritten_query": rewritten, "final_queries": [rewritten]}


async def decompose_query(state: ConversationState) -> dict:
    logger.info("[decompose_query] decomposing complex query")
    llm = _make_llm()
    chain = load_prompt("conversation/decompose_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    sub_questions = _parse_lines(result)

    if not sub_questions:
        sub_questions = [state["message"]]

    logger.info(f"[decompose_query] sub_questions={sub_questions}")
    return {"sub_questions": sub_questions, "final_queries": sub_questions}


async def hyde_query(state: ConversationState) -> dict:
    logger.info("[hyde_query] generating hypothetical document")
    llm = _make_llm()
    chain = load_prompt("conversation/hyde_query") | llm | StrOutputParser()
    hyde_doc = await chain.ainvoke({"question": state["message"]})
    hyde_doc = hyde_doc.strip()
    logger.info(f"[hyde_query] hyde_document length={len(hyde_doc)}")
    return {"hyde_document": hyde_doc, "final_queries": [state["message"], hyde_doc]}



async def expand_queries(state: ConversationState) -> dict:
    logger.info(f"[expand_queries] expanding {len(state['final_queries'])} queries")
    llm = _make_llm()
    chain = load_prompt("conversation/expand_queries") | llm | StrOutputParser()

    all_queries: List[str] = []
    seen: set = set()

    for query in state["final_queries"]:
        if query not in seen:
            all_queries.append(query)
            seen.add(query)

        result = await chain.ainvoke({"question": query, "n": 2})
        for variant in _parse_lines(result):
            if variant not in seen:
                all_queries.append(variant)
                seen.add(variant)

    logger.info(f"[expand_queries] total final_queries={len(all_queries)}")
    return {"final_queries": all_queries}

async def generate_response(state: ConversationState) -> dict:
    """Tổng hợp câu trả lời cuối cùng từ context đã retrieve → set response."""
    import json

    logger.info(f"[generate_response] final state after subgraph:")
    logger.info(f"{json.dumps(state, ensure_ascii=False, default=str, indent=2)}")
