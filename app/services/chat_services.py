"""
Chat Services — business logic xử lý tin nhắn qua graph.
"""
import uuid
from typing import Optional
from langchain_core.runnables import RunnableConfig

from app.graph.builder import main_graph
from app.graph.state import AppState
from app.schema.chat_schema import ChatRequest, ChatResponse
from app.schema.summary_schema import CVTemplate
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

        # --- Config cho MemorySaver (thread_id là session_id) ---
        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        # --- Build state ---
        # Load previous state từ MemorySaver checkpoint nếu có
        previous_state_values = None
        try:
            previous_state = main_graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
                logger.info(f"[process_message] loaded previous state from checkpoint")
        except Exception as e:
            logger.debug(f"[process_message] no previous checkpoint: {e}")

        # Nếu có previous state, merge vào; nếu không, tạo mới
        if previous_state_values:
            # QUAN TRỌNG: Preserve template cũ - cơ chế mới chỉ cập nhật các trường có dữ liệu
            previous_template = previous_state_values.get("template", {})
            logger.info(f"[process_message] preserving template from previous state: {previous_template}")

            state: AppState = {
                **previous_state_values,  # Inherit toàn bộ state cũ (bao gồm template cũ)
                "message": request.message,  # Update message mới
            }
        else:
            state: AppState = {
                "message": request.message,
                "intent": "ask",
                "current_phase": "conversation",
                "response": None,
                "template": CVTemplate().model_dump()
            }
            logger.info(f"[process_message] initialized new template")

        try:
            # --- Invoke graph ---
            # Cơ chế mới: extract_info chỉ cập nhật các trường có dữ liệu thực tế (không ghi đè null/rỗng)
            logger.info(f"[process_message] invoking main_graph with template: {state.get('template')}")
            result = await main_graph.ainvoke(state, config)

            # Handle response (có thể None từ subgraph)
            response_text = result.get("response") or "Không có phản hồi từ hệ thống"
            logger.info(f"[process_message] graph done | intent={result.get('intent')} | response_len={len(str(response_text))}")

            # Log template changes - chi tiết hơn để track cơ chế preserve
            result_template = result.get("template", {})
            logger.info(f"[process_message] updated template: {result_template}")

            # So sánh template để đảm bảo chỉ các trường có dữ liệu được cập nhật
            # Duyệt qua các key của CVTemplate.model_dump() để an toàn
            template_keys = CVTemplate().model_dump().keys()
            for field_name in template_keys:
                old_val_data = state.get("template", {})
                new_val_data = result_template

                # result_template có thể là CVTemplate object hoặc dict
                if isinstance(new_val_data, CVTemplate):
                    new_value = getattr(new_val_data, field_name, None)
                else:
                    new_value = new_val_data.get(field_name) if isinstance(new_val_data, dict) else None

                old_value = old_val_data.get(field_name) if isinstance(old_val_data, dict) else None

                if old_value != new_value:
                    logger.info(f"[process_message] template field '{field_name}' changed: {old_value} → {new_value}")

            # MemorySaver tự động persist state checkpoint, không cần save riêng

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
