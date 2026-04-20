from typing import Annotated, List, Literal
from typing_extensions import TypedDict
import operator


class ConversationState(TypedDict):
    # --- Input ---
    original_question: str                          # câu hỏi gốc từ user

    # --- Query Enhancement ---
    query_type: Literal["simple", "complex", "factual"]  # loại query sau khi phân tích
    rewritten_query: str                            # kết quả sau rewrite (simple)
    sub_questions: List[str]                        # câu hỏi con (complex)
    hyde_document: str                              # hypothetical document (factual)
    final_queries: List[str]                        # danh sách query cuối → đưa vào retrieval

    # --- Retrieval ---
    retrieved_docs: Annotated[List[str], operator.add]  # docs thu thập, cộng dồn qua các vòng lặp

    # --- Loop control ---
    iteration: int                                  # số vòng lặp hiện tại
    max_iterations: int                             # giới hạn vòng lặp (chống vòng lặp vô tận)
    has_enough_info: bool                           # cờ: đủ thông tin để đánh giá chưa
