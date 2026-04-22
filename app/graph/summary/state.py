from typing import Literal, Optional

from app.graph.state import AppState

class SummaryState(AppState):
  template: dict = {
    "name": None,
    "email": None,
    "phone": None,
    "education": None,
    "experience": None,
    "skills": [],
  }

  evaluation: Literal["incomplete", "complete"]
  iteration_count: int = 0
  max_iterations: int = 3

  


