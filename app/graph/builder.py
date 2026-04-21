"""
Parent Graph — entry point của toàn bộ hệ thống.

Flow:
  classify_intent
      ├── ask     → conversation_subgraph  (RAG pipeline)
      └── provide → summary_subgraph       (thu thập thông tin ứng viên)

Checkpointer: MemorySaver (v1).
Nâng cấp production: đổi thành AsyncRedisSaver — không cần sửa graph.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AppState
from app.graph.nodes import classify_intent
from app.graph.edges import route_by_intent
from app.graph.conversation.graph import conversation_graph


def build_main_graph():
    workflow = StateGraph(AppState)

    # --- Nodes ---
    workflow.add_node("classify_intent",      classify_intent)
    workflow.add_node("conversation_subgraph", conversation_graph)
    # workflow.add_node("summary_subgraph",      summary_graph)

    # # --- Entry point ---
    workflow.set_entry_point("classify_intent")

    # # --- Routing sau classify_intent ---
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "conversation_subgraph": "conversation_subgraph",
            # "interview_subgraph":    "summary_subgraph",
        },
    )

    # # --- Kết thúc ---
    workflow.add_edge("conversation_subgraph", END)
    # workflow.add_edge("summary_subgraph",      END)
    return workflow.compile(checkpointer=MemorySaver())


main_graph = build_main_graph()
