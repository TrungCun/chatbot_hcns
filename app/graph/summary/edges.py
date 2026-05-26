from typing import Literal

from app.graph.summary.state import SummaryState

def route_summary(state: SummaryState) -> str:
    evaluation = state.get("evaluation", "incomplete")
    summary_status = state.get("summary_status", "collecting")
    
    if evaluation == "incomplete":
        return "incomplete"
    
    if summary_status == "pending_confirmation":
        return "check_confirmation"
    elif summary_status == "confirmed":
        return "complete"
    else:
        return "ask_confirmation"

def route_check_confirmation(state: SummaryState) -> str:
    if state.get("summary_status") == "confirmed":
        return "confirmed"
    else:
        return "modify"
