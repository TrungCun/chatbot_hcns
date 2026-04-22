from typing import Literal

from app.graph.summary.state import SummaryState


def route_summary(state: SummaryState) -> Literal["complete", "incomplete"]:
    return state.get("evaluation", "incomplete")
