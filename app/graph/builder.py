from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AppState
from app.graph.nodes import classify_user_intent, update_context, save_history
from app.graph.edges import route_by_user_intent
from app.graph.conversation.graph import conversation_graph
from app.graph.summary.graph import summary_graph

def build_main_graph():
    workflow = StateGraph(AppState)

    # Nodes
    workflow.add_node("update_context", update_context)
    workflow.add_node("classify_user_intent", classify_user_intent)
    workflow.add_node("conversation_subgraph", conversation_graph)
    workflow.add_node("summary_subgraph", summary_graph)
    workflow.add_node("save_history", save_history)

    # Entry point
    workflow.set_entry_point("update_context")
    workflow.add_edge("update_context", "classify_user_intent")

    # Routing 
    workflow.add_conditional_edges(
        "classify_user_intent",
        route_by_user_intent,
        {
            "conversation_subgraph": "conversation_subgraph",
            "summary_subgraph": "summary_subgraph",
        },
    )

    # END
    workflow.add_edge("conversation_subgraph", "save_history")
    workflow.add_edge("summary_subgraph", "save_history")
    workflow.add_edge("save_history", END)

    return workflow.compile(
        checkpointer=MemorySaver()
        )

main_graph = build_main_graph()
