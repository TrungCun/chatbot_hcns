from typing import Literal, Optional
from typing_extensions import TypedDict
from pydantic import Field

from app.schema.summary_schema import CVTemplate

class AppState(TypedDict):
    message: str

    intent: Literal["ask", "provide"]  # Level 1: User intent classification

    template: CVTemplate = Field(default_factory=CVTemplate)
    response: Optional[str] = None