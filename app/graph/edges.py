from typing import Literal

from app.graph.state import AppState

def route_by_user_intent(
    state: AppState,
) -> Literal["conversation_subgraph", "summary_subgraph"]:

    intent = state.get("intent", "ask")
    if intent == "provide":
        return "summary_subgraph"
    return "conversation_subgraph"
