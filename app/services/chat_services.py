import uuid
import json
from langchain_core.runnables import RunnableConfig

from app.tools.helper import HelperTools
from app.graph.builder import main_graph
from app.graph.state import create_initial_state
from app.schema.chat_schema import ChatRequest, ChatResponse, FilePayload
from app.schema.summary_schema import CVTemplate

from app.log import get_logger
logger = get_logger(__name__)

class ChatService:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.graph = main_graph

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] Startingggggggggggggggggggggg")

        user_id = request.user_id
        session_id = request.session_id
        # Check user id and session id
        if not user_id or not session_id:
            raise ValueError("Thiếu user_id hoặc session_id.")

        logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] Received message: '{request.message}' with {len(request.files)} file(s) attached.")
        
        file_urls = []
        try:
            # 1. Trích xuất text cho LLM
            file_text = await HelperTools.process_files(request.files)
            # 2. Lưu file vật lý để lưu history
            file_urls = HelperTools.save_files_locally(request.files, user_id, session_id)
        except Exception as e:
            logger.error(f"[CHAT SERVICE / PROCESS MESSAGE] file processing error: {e}", exc_info=True)
            return ChatResponse(
                user_id=user_id,
                response="Lỗi xử lý file, vui lòng kiểm tra lại định dạng file.",
                session_id=session_id,
            )

        original_message = request.message.strip() if request.message else ""
        if file_text:
            if original_message:
                final_message = f"{original_message}\n\n[Tài liệu đính kèm]\n{file_text}"
            else:
                final_message = f"Tôi đã gửi tài liệu sau, hãy đọc và hỗ trợ tôi:\n\n{file_text}"
        else:
            final_message = original_message

        config: RunnableConfig = {
            "configurable": {
                "thread_id": f"{user_id}_{session_id}",
            }
        }

        previous_state_values = None
        try:
            previous_state = self.graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
                logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] tải state cũ từ checkpoint ")
        except Exception as e:
            logger.debug(f"[CHAT SERVICE / PROCESS MESSAGE] no previous checkpoint: {e}")

        state = create_initial_state(
            message=final_message,
            session_id=session_id,
            user_id=user_id,
            file_urls=file_urls,
            previous_state=previous_state_values
        )

        try:
            current_temp = HelperTools.ensure_dict(state.get('template', {}))
            logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] invoking graph with template:\n{json.dumps(current_temp, indent=4, ensure_ascii=False)}")
           
            result = await self.graph.ainvoke(state, config)

            response_text = result.get("response") or "ngại quá không biết nói gì"
            logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] graph done | intent={result.get('intent')} | response_text='{response_text[:50]}...'")

            result_template = HelperTools.ensure_dict(result.get("template", {}))
            logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] updated template:\n{json.dumps(result_template, indent=4, ensure_ascii=False)}")

            template_keys = CVTemplate.model_fields.keys()
            old_val_dict = current_temp
            new_val_dict = result_template

            # 3. Duyệt và so sánh
            for field_name in template_keys:
                old_value = old_val_dict.get(field_name)
                new_value = new_val_dict.get(field_name)

                if old_value != new_value:

                    # Format log cho đẹp và dễ đọc (Pretty Print)
                    old_str = json.dumps(old_value, ensure_ascii=False, indent=2) if isinstance(old_value, (dict, list)) else str(old_value)
                    new_str = json.dumps(new_value, ensure_ascii=False, indent=2) if isinstance(new_value, (dict, list)) else str(new_value)

                    logger.info(
                        f"\n[CHAT SERVICE / PROCESS MESSAGE] template field '{field_name}' changed:\n"
                        f"--- CŨ ---\n{old_str}\n"
                        f"--- MỚI ---\n{new_str}\n"
                        f"--------------------------------------------------"
                    )

            # --- Build response ---
            response = ChatResponse(
                user_id=user_id,
                response=response_text,
                session_id=session_id,
            )
            return response

        except Exception as e:
            logger.error(f"[CHAT SERVICE / PROCESS MESSAGE] error: {e}", exc_info=True)
            # Fallback
            return ChatResponse(
                user_id=user_id,
                response="Đang bận chút việc, chờ xíu nhé babe",
                session_id=session_id,
            )

    async def stream_message(self, request: ChatRequest):
        """Async generator yielding SSE chunks for streaming response."""
        # Các node sinh response cuối cùng cho người dùng
        RESPONSE_NODES = {"generate_response", "respond_complete", "respond_incomplete"}

        user_id = request.user_id
        session_id = request.session_id
        # Check user id and session id
        if not user_id or not session_id:
            raise ValueError("Thiếu user_id hoặc session_id.")
        
        logger.info(f"[CHAT SERVICE / PROCESS MESSAGE] Received message: '{request.message}' with {len(request.files)} file(s) attached.")

        file_urls = []
        try:
            # 1. Trích xuất text cho LLM
            file_text = await HelperTools.process_files(request.files)
            # 2. Lưu file vật lý để lưu history
            file_urls = HelperTools.save_files_locally(request.files, user_id, session_id)
        except Exception as e:
            logger.error(f"[CHAT SERVICE / STREAM MESSAGE] file processing error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Lỗi xử lý file'}, ensure_ascii=False)}\n\n"
            return

        original_message = request.message.strip() if request.message else ""
        if file_text:
            if original_message:
                final_message = f"{original_message}\n\n[Tài liệu đính kèm]\n{file_text}"
            else:
                final_message = f"Tôi đã gửi tài liệu sau, hãy đọc và hỗ trợ tôi:\n\n{file_text}"
        else:
            final_message = original_message

        config: RunnableConfig = {
            "configurable": {
                "thread_id": f"{user_id}_{session_id}"
                }}

        previous_state_values = None
        try:
            previous_state = self.graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
        except Exception as e:
            logger.debug(f"[CHAT SERVICE / STREAM MESSAGE] no previous checkpoint: {e}")

        state = create_initial_state(
            message=final_message,
            session_id=session_id,
            user_id=user_id,
            file_urls=file_urls,
            previous_state=previous_state_values,
        )

        try:
            async for event in self.graph.astream_events(state, config, version="v2"):
                event_name = event.get("event")

                if event_name == "on_chat_model_stream":
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    if node_name not in RESPONSE_NODES:
                        continue
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[CHAT SERVICE / STREAM MESSAGE] error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)[:100]}, ensure_ascii=False)}\n\n"


_service_instance = ChatService()

def get_chat_service() -> ChatService:
    return _service_instance