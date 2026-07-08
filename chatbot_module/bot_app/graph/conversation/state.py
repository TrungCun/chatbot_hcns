from typing import List, Literal

from bot_app.graph.state import AppState

class ConversationState(AppState):

    domain: Literal["job", "company", "chitchat"] 

    rewritten_query: str

    final_queries: List[str]

    retrieved_documents: List[str] = []
    reranked_documents: List[str] = []
    
    validation_result: Literal["pass", "fail"] = "pass"
    loop_count: int = 0
