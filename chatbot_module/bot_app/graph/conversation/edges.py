from typing import Literal

from bot_app.graph.conversation.state import ConversationState
from bot_app.log import get_logger
logger = get_logger(__name__)

def route_by_conversation_domain(
    state: ConversationState,
) -> Literal["handle_job_query", "rewrite_query", "handle_chitchat"]:
    """Route based on Level 2 Classification (job/company domain).
    Only used when intent='ask'.

    - 'job': Direct to handle_job_query to call list_all_jobs tool
    - 'company': Full RAG pipeline (simplified to rewrite_query -> retrieve_documents -> ...)
    - 'chitchat': Direct to a lightweight node to respond contextually without tools
    """
    domain = state.get("domain", "chitchat")

    routes = {
        "job": "handle_job_query",
        "company": "rewrite_query",
        "chitchat": "handle_chitchat",
    }

    return routes.get(domain, "handle_chitchat")
def route_after_validation(
    state: ConversationState,
) -> Literal["rewrite_query", "generate_response", "handle_job_query"]:
    """Decide whether to loop back to rewrite or proceed to response."""
    val_res = state.get("validation_result", "pass")
    domain = state.get("domain")
    
    if val_res == "fail":
        logger.info(f"[route_after_validation] Validation FAILED for domain {domain}. Looping back to rewrite.")
        return "rewrite_query"
        
    return "handle_job_query" if domain == "job" else "generate_response"