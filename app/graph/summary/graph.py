from langgraph.graph import StateGraph, END

from app.graph.summary.state import SummaryState
from app.graph.summary.nodes import extract_info, summary, respond_complete, respond_incomplete
from app.graph.summary.edges import route_summary

def build_summary_graph():
    workflow = StateGraph(SummaryState)

    # Nodes
    workflow.add_node("extract_info", extract_info)
    workflow.add_node("summary", summary)
    workflow.add_node("respond_complete", respond_complete)
    workflow.add_node("respond_incomplete", respond_incomplete)

    # Entry
    workflow.set_entry_point("extract_info")

    # Edges
    workflow.add_edge("extract_info", "summary")

    # Conditional branching after evaluation
    workflow.add_conditional_edges(
        "summary",
        route_summary,
        {
            "complete": "respond_complete",
            "incomplete": "respond_incomplete",
        }
    )

    workflow.add_edge("respond_complete", END)
    workflow.add_edge("respond_incomplete", END)

    return workflow.compile()


summary_graph = build_summary_graph()