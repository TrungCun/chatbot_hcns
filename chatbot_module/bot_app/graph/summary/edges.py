from typing import Literal

from bot_app.graph.summary.state import SummaryState

def route_entry(state: SummaryState) -> str:
    summary_status = state.get("summary_status", "collecting")
    if summary_status == "pending_confirmation":
        return "check_confirmation"
    return "extract_info"

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

