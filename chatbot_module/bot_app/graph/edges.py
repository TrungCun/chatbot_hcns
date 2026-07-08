from typing import Literal

from bot_app.graph.state import AppState

def route_by_user_intent(
    state: AppState,
) -> Literal["conversation_subgraph", "acknowledge_receipt"]:

    intent = state.get("intent", "ask")
    if intent == "provide":
        return "acknowledge_receipt"
    return "conversation_subgraph"
