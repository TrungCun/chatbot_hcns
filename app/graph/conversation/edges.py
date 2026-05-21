from typing import Literal

from app.graph.conversation.state import ConversationState

def route_by_query_complexity(
    state: ConversationState,
) -> Literal["rewrite_query", "decompose_query", "hyde_query"]:
    """Route based on Level 3 Classification (simple/complex/factual).
    Determines which RAG preprocessing strategy to use.
    """
    classify_query_complexity = state.get("classify_query_complexity", "simple")
    routes = {
        "simple":  "rewrite_query",
        "complex": "decompose_query",
        "factual": "hyde_query",
    }
    return routes.get(classify_query_complexity, "rewrite_query")

def route_by_conversation_domain(
    state: ConversationState,
) -> Literal["generate_response", "classify_query_complexity", "handle_chitchat"]:
    """Route based on Level 2 Classification (job/company domain).
    Only used when intent='ask'.

    - 'job': Direct to generate_response to call list_all_jobs tool
    - 'company': Full RAG pipeline (classify complexity → expand queries → generate_response)
    - 'chitchat': Direct to a lightweight node to respond contextually without tools
    """
    domain = state.get("domain", "chitchat")
    
    routes = {
        "job": "generate_response",
        "company": "classify_query_complexity",
        "chitchat": "handle_chitchat",
    }

    return routes.get(domain, "handle_chitchat")
