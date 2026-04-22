from typing import List, Literal

from app.graph.state import AppState

class ConversationState(AppState):

    query_type: Literal["simple", "complex", "factual"]

    rewritten_query: str
    sub_questions: List[str]
    hyde_document: str
    
    final_queries: List[str]