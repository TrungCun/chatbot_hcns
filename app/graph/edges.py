"""
Edges cho Parent Graph.
"""
from typing import Literal

from app.graph.state import AppState


def route_by_intent(
    state: AppState,
) -> Literal["conversation_subgraph", "interview_subgraph"]:
    """
    Sau classify_intent → chọn subgraph phù hợp:
      ask     → conversation_subgraph  (RAG: hỏi về công ty / vị trí)
      provide → interview_subgraph     (thu thập thông tin ứng viên)
    """
    intent = state.get("intent", "ask")
    if intent == "provide":
        return "interview_subgraph"
    return "conversation_subgraph"
