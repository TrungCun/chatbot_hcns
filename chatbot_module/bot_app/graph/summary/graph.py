from langgraph.graph import StateGraph, END

from bot_app.graph.summary.state import SummaryState
from bot_app.graph.summary.nodes import extract_info, respond_complete, evaluation

def build_summary_graph():
    workflow = StateGraph(SummaryState)

    # Nodes
    workflow.add_node("extract_info", extract_info)
    workflow.add_node("evaluation", evaluation)
    workflow.add_node("respond_complete", respond_complete)

    # Entry
    workflow.set_entry_point("extract_info")

    # Edges
    workflow.add_edge("extract_info", "evaluation")
    workflow.add_edge("evaluation", "respond_complete")
    workflow.add_edge("respond_complete", END)

    # Interrupt before extract_info so background task can pick it up
    return workflow.compile(interrupt_before=["extract_info"])


summary_graph = build_summary_graph()