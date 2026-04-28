from typing import Literal, Optional, List
from typing_extensions import TypedDict
from pydantic import Field

from app.schema.summary_schema import CVTemplate
from app.schema.chat_schema import Attachment

class AppState(TypedDict):
    session_id: str
    message: str
    attachments: Optional[List[Attachment]] = None

    intent: Literal["ask", "provide"]

    template: CVTemplate = Field(default_factory=CVTemplate)
    summary: Optional[str] = None
    response: Optional[str] = None