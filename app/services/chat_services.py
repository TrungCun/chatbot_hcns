import uuid
import json
from langchain_core.runnables import RunnableConfig

from app.graph.builder import main_graph
from app.graph.state import AppState
from app.schema.chat_schema import ChatRequest, ChatResponse
from app.schema.summary_schema import CVTemplate

from app.log import get_logger
logger = get_logger(__name__)


class ChatService:

    @staticmethod
    async def process_message(request: ChatRequest) -> ChatResponse:

        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"[process_message] session_id={session_id}")

        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        previous_state_values = None
        try:
            previous_state = main_graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
                logger.info(f"[process_message] loaded previous state from checkpoint")
        except Exception as e:
            logger.debug(f"[process_message] no previous checkpoint: {e}")

        if previous_state_values:
            previous_template = previous_state_values.get("template", {})

            # Xử lý an toàn: Chuyển Pydantic Object thành Dict trước khi log
            template_to_log = previous_template.model_dump() if hasattr(previous_template, "model_dump") else previous_template

            logger.info(f"[process_message] preserving template from previous state:\n{json.dumps(template_to_log, indent=4, ensure_ascii=False)}")

            state: AppState = {
                **previous_state_values,
                 "session_id": session_id,
                "message": request.message,
                "attachments": request.attachments,
            }
        else:
            state: AppState = {
                "session_id": session_id,
                "message": request.message,
                "attachments": request.attachments,
                "intent": "ask",
                "current_phase": "conversation",
                "response": None,
                "template": CVTemplate().model_dump()
            }
            logger.info(f"[process_message] initialized new template")

        try:
            current_temp = state.get('template', {})
            temp_to_log = current_temp.model_dump() if hasattr(current_temp, "model_dump") else current_temp

            logger.info(f"[process_message] invoking main_graph with template:\n{json.dumps(temp_to_log, indent=4, ensure_ascii=False)}")

            result = await main_graph.ainvoke(state, config)

            response_text = result.get("response") or "không biết nói gì"

            logger.info(f"[process_message] graph done | intent={result.get('intent')} | response_text='{response_text[:50]}...'")

            result_template = result.get("template", {})
            if hasattr(result_template, "model_dump"):
                printable_template = result_template.model_dump()
            else:
                printable_template = result_template
            logger.info(f"[process_message] updated template:\n{json.dumps(printable_template, indent=4, ensure_ascii=False)}")


            template_keys = CVTemplate.model_fields.keys()
            old_val_data = state.get("template", {})
            new_val_data = result_template

            for field_name in template_keys:
                if isinstance(new_val_data, CVTemplate):
                    new_value = getattr(new_val_data, field_name, None)
                else:
                    new_value = new_val_data.get(field_name) if isinstance(new_val_data, dict) else None

                old_value = old_val_data.get(field_name) if isinstance(old_val_data, dict) else None

                if old_value != new_value:
                    logger.info(f"[process_message] template field '{field_name}' changed:\n- CŨ : {old_value}\n- MỚI: {new_value}")

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
            # Fallback
            return ChatResponse(
                response=f"Lỗi hệ thống: {str(e)[:100]}",
                intent="ask",
                session_id=session_id,
                current_phase="conversation",
            )


async def chat_message(request: ChatRequest) -> ChatResponse:
    return await ChatService.process_message(request)
