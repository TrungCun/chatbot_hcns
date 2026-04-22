from langgraph.graph import StateGraph, END

from app.graph.conversation.state import ConversationState
from app.graph.conversation.edges import route_by_query_type
from app.graph.conversation.nodes import (
    analyze_query,
    rewrite_query,
    decompose_query,
    hyde_query,
    expand_queries,
    generate_response
)

def build_conversation_graph():
    workflow = StateGraph(ConversationState)

    # Nodes
    workflow.add_node("analyze_query",      analyze_query)
    workflow.add_node("rewrite_query",      rewrite_query)
    workflow.add_node("decompose_query",    decompose_query)
    workflow.add_node("hyde_query",         hyde_query)
    workflow.add_node("expand_queries",     expand_queries)
    # log state subgraph
    workflow.add_node("generate_response",  generate_response)
    # Entry
    workflow.set_entry_point("analyze_query")

    # analyze_query
    workflow.add_conditional_edges(
        "analyze_query",
        route_by_query_type,
        {
            "rewrite_query":   "rewrite_query",
            "decompose_query": "decompose_query",
            "hyde_query":      "hyde_query",
        },
    )

    workflow.add_edge("rewrite_query",   "expand_queries")
    workflow.add_edge("decompose_query", "expand_queries")
    workflow.add_edge("hyde_query",      "expand_queries")

    workflow.add_edge("expand_queries",    "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()

conversation_graph = build_conversation_graph()

