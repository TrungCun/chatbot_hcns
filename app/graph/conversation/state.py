from typing import List, Literal

from app.graph.state import AppState

class ConversationState(AppState):

    domain: Literal["job", "company", "chitchat"] 
    classify_query_complexity: Literal["simple", "complex", "factual"]

    rewritten_query: str
    sub_questions: List[str]
    hyde_document: str

    final_queries: List[str]

    retrieved_documents: List[str] = []
    reranked_documents: List[str] = []
