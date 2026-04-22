from typing import Literal, Optional
from typing_extensions import TypedDict


class AppState(TypedDict):
    message: str

    intent: Literal["ask", "provide"]
    current_phase: Literal["conversation", "interview"]

    response: Optional[str]
