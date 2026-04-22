"""
Chat Services — business logic xử lý tin nhắn qua graph.
"""
import uuid
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from app.graph.builder import main_graph
from app.graph.state import AppState
from app.schema import ChatRequest, ChatResponse
from app.log import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service xử lý chat logic."""

    @staticmethod
    async def process_message(request: ChatRequest) -> ChatResponse:
        """
        Xử lý message từ user — route qua graph, trả về response.

        Args:
            request: ChatRequest với message và session_id (optional).

        Returns:
            ChatResponse với response, intent, session_id, current_phase.

        Raises:
            Exception: Nếu graph invoke thất bại.
        """
        # --- Session management ---
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"[process_message] session_id={session_id}, message='{request.message[:50]}...'")

        # --- Build state ---
        state: AppState = {
            "message": request.message,
            "intent": "ask",  # default, sẽ được override bởi classify_intent node
            "current_phase": "conversation",  # default
            "response": None,
        }

        # --- Config cho MemorySaver (thread_id là session_id) ---
        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        try:
            # --- Invoke graph ---
            logger.info(f"[process_message] invoking main_graph...")
            result = await main_graph.ainvoke(state, config)

            # Handle response (có thể None từ subgraph)
            response_text = result.get("response") or "Không có phản hồi từ hệ thống"
            logger.info(f"[process_message] graph done | intent={result.get('intent')} | response_len={len(str(response_text))}")
            logger.info(f"[process_message] state: {state}") # Log state để debug

            # --- Build response ---
            response = ChatResponse(
                response=response_text,
                intent=result.get("intent", "ask"),
                session_id=session_id,
                current_phase=result.get("current_phase", "conversation"),
            )
            return response

        except Exception as e:
            logger.error(f"[process_message] error: {e}", exc_info=True)
            # Fallback response
            return ChatResponse(
                response=f"Lỗi hệ thống: {str(e)[:100]}",
                intent="ask",
                session_id=session_id,
                current_phase="conversation",
            )


async def chat_message(request: ChatRequest) -> ChatResponse:
    """
    Wrapper function cho API endpoint — dễ test, dễ mock.

    Args:
        request: ChatRequest

    Returns:
        ChatResponse
    """
    return await ChatService.process_message(request)
