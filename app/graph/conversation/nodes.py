"""
Nodes cho conversation subgraph.

Thứ tự thực thi trong Query Enhancement:
  analyze_query → rewrite_query | decompose_query | hyde_query → expand_queries
"""
from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.graph.conversation.state import ConversationState
from app.prompt.loader import load_prompt
from app.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm() -> ChatOpenAI:
    from app.model.llm import get_llm
    return get_llm(stream=False)


def _parse_lines(text: str) -> List[str]:
    """Tách text nhiều dòng thành list, bỏ dòng trống."""
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Node 1: analyze_query
# ---------------------------------------------------------------------------

async def analyze_query(state: ConversationState) -> dict:
    """Phân loại query → xác định strategy nào sẽ được dùng."""
    logger.info(f"[analyze_query] question='{state['message']}'")
    llm = _make_llm()
    chain = load_prompt("conversation/analyze_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    query_type = result.strip().lower()

    # Fallback an toàn nếu LLM trả về giá trị không hợp lệ
    if query_type not in ("simple", "complex", "factual"):
        query_type = "simple"

    logger.info(f"[analyze_query] query_type='{query_type}'")
    logger.info(state)
    return {"query_type": query_type, **state}


# ---------------------------------------------------------------------------
# Node 2a: rewrite_query  (dùng cho simple)
# ---------------------------------------------------------------------------

async def rewrite_query(state: ConversationState) -> dict:
    """Rewrite cho simple query."""
    logger.info("[rewrite_query] rewriting simple query")
    llm = _make_llm()
    chain = load_prompt("conversation/rewrite_query") | llm | StrOutputParser()
    rewritten = await chain.ainvoke({"question": state["message"]})
    rewritten = rewritten.strip()
    logger.info(f"[rewrite_query] result='{rewritten}'")
    return {"rewritten_query": rewritten, "final_queries": [rewritten], **state}


# ---------------------------------------------------------------------------
# Node 2b: decompose_query  (dùng cho complex)
# ---------------------------------------------------------------------------

async def decompose_query(state: ConversationState) -> dict:
    """Tách complex query thành sub-questions."""
    logger.info("[decompose_query] decomposing complex query")
    llm = _make_llm()
    chain = load_prompt("conversation/decompose_query") | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["message"]})
    sub_questions = _parse_lines(result)

    # Đảm bảo luôn có ít nhất câu hỏi gốc nếu decompose thất bại
    if not sub_questions:
        sub_questions = [state["message"]]

    logger.info(f"[decompose_query] sub_questions={sub_questions}")
    return {"sub_questions": sub_questions, "final_queries": sub_questions, **state}


# ---------------------------------------------------------------------------
# Node 2c: hyde_query  (dùng cho factual)
# ---------------------------------------------------------------------------

async def hyde_query(state: ConversationState) -> dict:
    """Tạo hypothetical document cho factual query."""
    logger.info("[hyde_query] generating hypothetical document")
    llm = _make_llm()
    chain = load_prompt("conversation/hyde_query") | llm | StrOutputParser()
    hyde_doc = await chain.ainvoke({"question": state["message"]})
    hyde_doc = hyde_doc.strip()
    logger.info(f"[hyde_query] hyde_document length={len(hyde_doc)}")
    return {"hyde_document": hyde_doc, "final_queries": [state["message"], hyde_doc], **state}


# ---------------------------------------------------------------------------
# Node 3: expand_queries
# ---------------------------------------------------------------------------

async def expand_queries(state: ConversationState) -> dict:
    """Sinh thêm multi-query variants, dedup và trả về final_queries đầy đủ."""
    logger.info(f"[expand_queries] expanding {len(state['final_queries'])} queries")
    llm = _make_llm()
    chain = load_prompt("conversation/expand_queries") | llm | StrOutputParser()

    all_queries: List[str] = []
    seen: set = set()

    for query in state["final_queries"]:
        # Giữ query gốc
        if query not in seen:
            all_queries.append(query)
            seen.add(query)

        # Sinh thêm 2 variants cho mỗi query
        result = await chain.ainvoke({"question": query, "n": 2})
        for variant in _parse_lines(result):
            if variant not in seen:
                all_queries.append(variant)
                seen.add(variant)

    logger.info(f"[expand_queries] total final_queries={len(all_queries)}")
    return {"final_queries": all_queries, **state}


# ---------------------------------------------------------------------------
# Node 4: generate_response  (placeholder — retrieval chưa triển khai)
# Node cuối của subgraph, set `response` để trả về AppState.
# Khi retrieval + synthesis hoàn chỉnh, node này sẽ tổng hợp từ retrieved_docs.
# ---------------------------------------------------------------------------

async def generate_response(state: ConversationState) -> dict:
    """Tổng hợp câu trả lời cuối cùng từ context đã retrieve → set response."""
    logger.info("[generate_response] generating final response")

    # TODO: thay bằng LLM synthesis từ retrieved_docs khi retrieval hoàn chỉnh
    final_queries = state.get("final_queries", [])
    response = (
        f"[Đang xử lý] Đã chuẩn bị {len(final_queries)} query để tìm kiếm. "
        f"Retrieval chưa được triển khai."
    )

    logger.info(f"[generate_response] response set (length={len(response)})")
    return {"response": response, **state}
