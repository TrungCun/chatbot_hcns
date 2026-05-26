from langgraph.graph import StateGraph, END

from app.graph.summary.state import SummaryState
from app.graph.summary.nodes import extract_info, summary, respond_complete, respond_incomplete, evaluation, ask_confirmation, check_confirmation
from app.graph.summary.edges import route_summary, route_check_confirmation

def build_summary_graph():
    workflow = StateGraph(SummaryState)

    # Nodes
    workflow.add_node("extract_info", extract_info)
    workflow.add_node("summary", summary)
    workflow.add_node("respond_complete", respond_complete)
    workflow.add_node("respond_incomplete", respond_incomplete)
    workflow.add_node("evaluation", evaluation)
    workflow.add_node("ask_confirmation", ask_confirmation)
    workflow.add_node("check_confirmation", check_confirmation)

    # Entry
    workflow.set_entry_point("extract_info")

    # Edges
    workflow.add_edge("extract_info", "summary")

    # Conditional branching after summary
    workflow.add_conditional_edges(
        "summary",
        route_summary,
        {
            "complete": "evaluation",
            "incomplete": "respond_incomplete",
            "ask_confirmation": "ask_confirmation",
            "check_confirmation": "check_confirmation"
        }
    )
    
    # Conditional branching after check_confirmation
    workflow.add_conditional_edges(
        "check_confirmation",
        route_check_confirmation,
        {
            "confirmed": "evaluation",
            "modify": "ask_confirmation"
        }
    )

    workflow.add_edge("ask_confirmation", END)
    workflow.add_edge("evaluation", "respond_complete")
    workflow.add_edge("respond_complete", END)
    workflow.add_edge("respond_incomplete", END)

    return workflow.compile()


summary_graph = build_summary_graph()