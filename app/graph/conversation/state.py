from typing import Annotated, List, Literal, Optional
from typing_extensions import TypedDict
import operator

from app.graph.state import AppState


class ConversationState(AppState):
    """
    State nội bộ của Conversation Subgraph.

    Kế thừa AppState — các field của AppState (message, intent,
    current_phase, response) tự động có ở đây.

    Các field bên dưới là PRIVATE của subgraph này:
    parent graph không đọc chúng, chỉ nhận lại `response` sau khi subgraph END.
    """

    # --- Query Enhancement (private) ---
    query_type: Literal["simple", "complex", "factual"]  # loại query sau khi phân tích
    rewritten_query: str                            # kết quả sau rewrite (simple)
    sub_questions: List[str]                        # câu hỏi con (complex)
    hyde_document: str                              # hypothetical document (factual)
    final_queries: List[str]                        # danh sách query cuối → đưa vào retrieval

    # # --- Retrieval (private) ---
    # retrieved_docs: Annotated[List[str], operator.add]  # docs thu thập, cộng dồn qua các vòng lặp

    # # --- Loop control (private) ---
    # iteration: int                                  # số vòng lặp hiện tại
    # max_iterations: int                             # giới hạn vòng lặp (chống vòng lặp vô tận)
    # has_enough_info: bool                           # cờ: đủ thông tin để tổng hợp chưa
