from langgraph.graph import StateGraph, END

from app.graph.conversation.state import ConversationState
from app.graph.conversation.edges import route_by_query_complexity, route_by_conversation_domain
from app.graph.conversation.nodes import (
    classify_conversation_domain,
    classify_query_complexity,
    rewrite_query,
    decompose_query,
    hyde_query,
    expand_queries,
    generate_response
)

def build_conversation_graph():
    workflow = StateGraph(ConversationState)

    # Nodes
    workflow.add_node("classify_conversation_domain", classify_conversation_domain)
    workflow.add_node("classify_query_complexity", classify_query_complexity)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("decompose_query", decompose_query)
    workflow.add_node("hyde_query", hyde_query)
    workflow.add_node("expand_queries", expand_queries)
    workflow.add_node("generate_response", generate_response)

    # Entry
    workflow.set_entry_point("classify_conversation_domain")
    # Level 2 Routing: job vs company
    workflow.add_conditional_edges(
        "classify_conversation_domain",
        route_by_conversation_domain,
        {
            "generate_response": "generate_response",  # Job path: direct to response
            "classify_query_complexity": "classify_query_complexity",  # Company path: RAG pipeline
        },
    )

    # Level 3 Routing: simple/complex/factual (only for company questions)
    workflow.add_conditional_edges(
        "classify_query_complexity",
        route_by_query_complexity,
        {
            "rewrite_query": "rewrite_query",
            "decompose_query": "decompose_query",
            "hyde_query": "hyde_query",
        },
    )

    workflow.add_edge("rewrite_query", "expand_queries")
    workflow.add_edge("decompose_query", "expand_queries")
    workflow.add_edge("hyde_query", "expand_queries")
    workflow.add_edge("expand_queries", "generate_response")
    
    # Both paths (job and company) end at generate_response → END
    workflow.add_edge("generate_response", END)

    return workflow.compile()

conversation_graph = build_conversation_graph()

