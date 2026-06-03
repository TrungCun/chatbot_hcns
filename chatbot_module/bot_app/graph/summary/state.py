from typing import Literal
from pydantic import Field


from bot_app.graph.state import AppState
from bot_app.schema.summary_schema import CVTemplate

class SummaryState(AppState):
    template: CVTemplate = Field(default_factory=CVTemplate)
    evaluation: Literal["incomplete", "complete"]