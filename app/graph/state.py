from typing import Literal, Optional
from typing_extensions import TypedDict
from pydantic import Field

from app.schema.summary_schema import CVTemplate

class AppState(TypedDict):
    message: str

    intent: Literal["ask", "provide"]

    template: CVTemplate = Field(default_factory=CVTemplate)
    summary: Optional[str] = None
    response: Optional[str] = None