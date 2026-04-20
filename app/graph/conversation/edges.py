"""
Edge routers cho conversation subgraph.
"""
from typing import Literal
from app.graph.conversation.state import ConversationState


def route_by_query_type(
    state: ConversationState,
) -> Literal["rewrite_query", "decompose_query", "hyde_query"]:
    """
    Sau analyze_query → chọn strategy phù hợp:
      simple  → rewrite_query
      complex → decompose_query
      factual → hyde_query
    """
    query_type = state.get("query_type", "simple")
    routes = {
        "simple":  "rewrite_query",
        "complex": "decompose_query",
        "factual": "hyde_query",
    }
    return routes.get(query_type, "rewrite_query")
