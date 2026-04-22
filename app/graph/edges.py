from typing import Literal

from app.graph.state import AppState

def route_by_intent(
    state: AppState,
) -> Literal["conversation_subgraph", "interview_subgraph"]:
    
    intent = state.get("intent", "ask")
    if intent == "provide":
        return "interview_subgraph"
    return "conversation_subgraph"
