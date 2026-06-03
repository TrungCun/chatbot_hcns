from langgraph.graph import StateGraph, END

from bot_app.graph.conversation.state import ConversationState
from bot_app.graph.conversation.edges import route_by_conversation_domain, route_after_validation
from bot_app.graph.conversation.nodes import (
    classify_conversation_domain,
    handle_chitchat,
    handle_job_query,
    rewrite_query,
    retrieve_documents,
    rerank_documents,
    generate_response,
    validate_retrieval
)

def build_conversation_graph():
    workflow = StateGraph(ConversationState)

    # Nodes
    workflow.add_node("classify_conversation_domain", classify_conversation_domain)
    workflow.add_node("handle_chitchat", handle_chitchat)
    workflow.add_node("handle_job_query", handle_job_query)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("rerank_documents", rerank_documents)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("validate_retrieval", validate_retrieval)

    # Entry
    workflow.set_entry_point("classify_conversation_domain")

    # 1. Routing theo Domain
    workflow.add_conditional_edges(
        "classify_conversation_domain",
        route_by_conversation_domain,
        {
            "handle_job_query": "handle_job_query",    # Nhánh job xử lý trực tiếp
            "rewrite_query": "rewrite_query",          # Nhánh company đi rewrite
            "handle_chitchat": "handle_chitchat",      # Chitchat đi thẳng
        },
    )

    # 2. Luồng Company RAG
    workflow.add_edge("rewrite_query", "retrieve_documents")
    workflow.add_edge("retrieve_documents", "rerank_documents")
    workflow.add_edge("rerank_documents", "validate_retrieval")

    # 3. Validation Loop (Tiền kiểm)
    workflow.add_conditional_edges(
        "validate_retrieval",
        route_after_validation,
        {
            "rewrite_query": "rewrite_query",         # Thất bại: Loop lại để rewrite (max 1 lần)
            "generate_response": "generate_response", # Thành công nhánh company
            "handle_job_query": "handle_job_query"    # Thành công nhánh job
        }
    )

    # 4. Final Response -> END (Giữ được streaming)
    workflow.add_edge("handle_job_query", END)
    workflow.add_edge("generate_response", END)
    workflow.add_edge("handle_chitchat", END)

    return workflow.compile()

conversation_graph = build_conversation_graph()

