from typing import Literal
from pydantic import Field


from app.graph.state import AppState
from app.schema.summary_schema import CVTemplate

class SummaryState(AppState):
    template: CVTemplate = Field(default_factory=CVTemplate)
    evaluation: Literal["incomplete", "complete"]
    iteration_count: int = 0
    max_iterations: int = 3