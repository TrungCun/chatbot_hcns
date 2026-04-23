from typing import Literal, Optional
from typing_extensions import TypedDict


class AppState(TypedDict):
    message: str

    intent: Literal["ask", "provide"]  # Level 1: User intent classification

    template: dict
    response: Optional[str] = None