"""
Nodes cho conversation subgraph.

Thứ tự thực thi trong Query Enhancement:
  analyze_query → rewrite_query | decompose_query | hyde_query → expand_queries
"""
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.graph.conversation.state import ConversationState
from app.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm() -> ChatOpenAI:
    """LLM phụ nhẹ dùng riêng cho query enhancement (không stream)."""
    from app.model.llm import get_llm
    return get_llm(stream=False)


def _parse_lines(text: str) -> List[str]:
    """Tách text nhiều dòng thành list, bỏ dòng trống."""
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Node 1: analyze_query
# Phân loại query để chọn đúng enhancement strategy
# ---------------------------------------------------------------------------

_ANALYZE_PROMPT = ChatPromptTemplate.from_template(
    """Bạn là hệ thống phân loại câu hỏi cho chatbot Hành chính Nhân sự (HCNS).

Phân loại câu hỏi sau thành đúng 1 trong 3 loại:
- simple  : câu hỏi đơn giản, 1 chủ đề, cần tìm kiếm trực tiếp
- complex : câu hỏi nhiều chủ đề hoặc nhiều ý, cần tách nhỏ để tìm
- factual : câu hỏi hỏi về số liệu, quy định, con số cụ thể

Chỉ trả về đúng 1 từ: simple | complex | factual

Câu hỏi: {question}
Loại:"""
)


async def analyze_query(state: ConversationState) -> dict:
    """Phân loại query → xác định strategy nào sẽ được dùng."""
    logger.info(f"[analyze_query] question='{state['original_question']}'")
    llm = _make_llm()
    chain = _ANALYZE_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["original_question"]})
    query_type = result.strip().lower()

    # Fallback an toàn nếu LLM trả về giá trị không hợp lệ
    if query_type not in ("simple", "complex", "factual"):
        query_type = "simple"

    logger.info(f"[analyze_query] query_type='{query_type}'")
    return {
        "query_type": query_type,
        "iteration": state.get("iteration", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Node 2a: rewrite_query  (dùng cho simple)
# Viết lại câu hỏi ngắn/mơ hồ thành rõ ràng, đầy đủ hơn
# ---------------------------------------------------------------------------

_REWRITE_PROMPT = ChatPromptTemplate.from_template(
    """Bạn là chuyên gia cải thiện câu hỏi tìm kiếm cho hệ thống HCNS.

Viết lại câu hỏi sau để tìm kiếm hiệu quả hơn trong tài liệu nội quy công ty:
- Làm rõ nghĩa, thêm context nếu thiếu
- Dùng từ ngữ chính thức, đầy đủ (không viết tắt)
- Chỉ trả về câu hỏi đã viết lại, không giải thích

Câu hỏi gốc: {question}
Câu hỏi viết lại:"""
)


async def rewrite_query(state: ConversationState) -> dict:
    """Rewrite cho simple query."""
    logger.info("[rewrite_query] rewriting simple query")
    llm = _make_llm()
    chain = _REWRITE_PROMPT | llm | StrOutputParser()
    rewritten = await chain.ainvoke({"question": state["original_question"]})
    rewritten = rewritten.strip()
    logger.info(f"[rewrite_query] result='{rewritten}'")
    return {
        "rewritten_query": rewritten,
        "final_queries": [rewritten],
    }


# ---------------------------------------------------------------------------
# Node 2b: decompose_query  (dùng cho complex)
# Tách câu hỏi nhiều ý thành các câu hỏi con độc lập
# ---------------------------------------------------------------------------

_DECOMPOSE_PROMPT = ChatPromptTemplate.from_template(
    """Bạn là chuyên gia phân tích câu hỏi cho hệ thống HCNS.

Tách câu hỏi sau thành tối đa 3 câu hỏi con độc lập.
Mỗi câu hỏi con phải:
- Có thể tìm kiếm độc lập trong tài liệu nội quy
- Rõ ràng, đầy đủ không cần context câu gốc
- Mỗi câu trên 1 dòng, không đánh số, không bullet

Câu hỏi gốc: {question}
Câu hỏi con:"""
)


async def decompose_query(state: ConversationState) -> dict:
    """Tách complex query thành sub-questions."""
    logger.info("[decompose_query] decomposing complex query")
    llm = _make_llm()
    chain = _DECOMPOSE_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({"question": state["original_question"]})
    sub_questions = _parse_lines(result)

    # Đảm bảo luôn có ít nhất câu hỏi gốc nếu decompose thất bại
    if not sub_questions:
        sub_questions = [state["original_question"]]

    logger.info(f"[decompose_query] sub_questions={sub_questions}")
    return {
        "sub_questions": sub_questions,
        "final_queries": sub_questions,
    }


# ---------------------------------------------------------------------------
# Node 2c: hyde_query  (dùng cho factual)
# Tạo hypothetical document → embed doc này thay vì embed query
# Giúp tìm kiếm chính xác hơn cho câu hỏi về số liệu/quy định
# ---------------------------------------------------------------------------

_HYDE_PROMPT = ChatPromptTemplate.from_template(
    """Viết một đoạn văn ngắn (~100 từ) như thể đây là nội dung trích từ
tài liệu nội quy công ty, trả lời trực tiếp cho câu hỏi sau.
Chỉ viết nội dung thuần túy, không thêm câu giới thiệu.

Câu hỏi: {question}
Đoạn nội dung:"""
)


async def hyde_query(state: ConversationState) -> dict:
    """Tạo hypothetical document cho factual query."""
    logger.info("[hyde_query] generating hypothetical document")
    llm = _make_llm()
    chain = _HYDE_PROMPT | llm | StrOutputParser()
    hyde_doc = await chain.ainvoke({"question": state["original_question"]})
    hyde_doc = hyde_doc.strip()
    logger.info(f"[hyde_query] hyde_document length={len(hyde_doc)}")
    return {
        "hyde_document": hyde_doc,
        "final_queries": [hyde_doc],    # embed doc này thay vì query gốc
    }


# ---------------------------------------------------------------------------
# Node 3: expand_queries
# Tạo thêm multi-query variants cho mỗi query trong final_queries
# Chạy sau tất cả 3 strategy trên
# ---------------------------------------------------------------------------

_EXPAND_PROMPT = ChatPromptTemplate.from_template(
    """Tạo {n} cách diễn đạt khác nhau cho câu hỏi sau, phù hợp tìm kiếm trong tài liệu HCNS.
Mỗi cách trên 1 dòng. Không đánh số, không bullet.

Câu hỏi gốc: {question}
Các cách diễn đạt khác:"""
)


async def expand_queries(state: ConversationState) -> dict:
    """Sinh thêm multi-query variants, dedup và trả về final_queries đầy đủ."""
    logger.info(f"[expand_queries] expanding {len(state['final_queries'])} queries")
    llm = _make_llm()
    chain = _EXPAND_PROMPT | llm | StrOutputParser()

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
    return {"final_queries": all_queries}
