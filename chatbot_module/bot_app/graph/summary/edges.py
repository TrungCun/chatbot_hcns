from typing import Literal

from bot_app.graph.summary.state import SummaryState

def route_entry(state: SummaryState) -> str:
    return "acknowledge_receipt"

def route_summary(state: SummaryState) -> str:
    evaluation = state.get("evaluation", "incomplete")
    if evaluation == "incomplete":
        return "incomplete"
    return "complete"

