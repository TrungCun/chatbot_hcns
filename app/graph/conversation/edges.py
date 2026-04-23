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
) -> Literal["generate_response", "classify_query_complexity"]:
    """Route based on Level 2 Classification (job/company domain).
    Only used when intent='ask'.

    - 'job': Direct to generate_response to call list_all_jobs tool
    - 'company': Full RAG pipeline (classify complexity → expand queries → generate_response)
    """
    domain = state.get("domain", "company")
    if domain == "job":
        return "generate_response"
    return "classify_query_complexity"
    return "classify_query_complexity"
    return "conversation_subgraph"
