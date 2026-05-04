import base64
import uuid
import json
from typing import List, Tuple
from langchain_core.runnables import RunnableConfig

from app.graph.builder import main_graph
from app.graph.state import AppState
from app.schema.chat_schema import ChatRequest, ChatResponse, Attachment
from app.schema.summary_schema import CVTemplate
from app.tools.pdf_handler import process_pdf_to_text

from app.log import get_logger
logger = get_logger(__name__)

class ChatService:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.graph = main_graph

    async def _process_files(self, files: List) -> Tuple[str, List[Attachment]]:
        attachments = []
        extracted_texts = []

        for file_payload in files:
            file_content = file_payload.content
            filename = file_payload.filename
            content_type = file_payload.content_type

            if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
                try:
                    text = await process_pdf_to_text(file_content, filename)

                    if isinstance(text, str):
                        extracted_texts.append(text)

                    logger.info(f"[ChatService] PDF '{filename}' extracted successfully.")
                except Exception as e:
                    logger.error(f"[ChatService] Failed to extract PDF {filename}: {e}")
            else:
                base64_content = base64.b64encode(file_content).decode("utf-8")
                logger.info(f"[ChatService] File '{filename}' encoded to base64 successfully.")
                attachments.append(Attachment(
                    filename=filename,
                    content_type=content_type,
                    content=base64_content
                ))

        pdf_combined_text = "\n\n".join(extracted_texts) if extracted_texts else ""
        return pdf_combined_text, attachments


    async def process_message(self, request: ChatRequest) -> ChatResponse:

        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"[process_message] session_id={session_id}")

        pdf_text, final_attachments = await self._process_files(request.files)

        original_message = request.message.strip() if request.message else ""
        if pdf_text:
            final_message = f"{original_message}\n\n[Tài liệu đính kèm]\n{pdf_text}"
        else:
            final_message = original_message

        if not final_message and final_attachments:
            final_message = "[Người dùng đã gửi tệp đính kèm]"

        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
            }
        }

        previous_state_values = None
        try:
            previous_state = self.graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
                logger.info(f"[process_message] loaded previous state from checkpoint")
        except Exception as e:
            logger.debug(f"[process_message] no previous checkpoint: {e}")

        if previous_state_values:
            previous_template = previous_state_values.get("template", {})

            #logger
            template_to_log = previous_template.model_dump() if hasattr(previous_template, "model_dump") else previous_template
            logger.info(f"[process_message] preserving template from previous state:\n{json.dumps(template_to_log, indent=4, ensure_ascii=False)}")

            state: AppState = {
                **previous_state_values,
                "session_id": session_id,
                "message": final_message,
                "attachments": final_attachments
            }
        else:
            state: AppState = {
                "session_id": session_id,
                "message": final_message,
                "attachments": final_attachments,
                "intent": "ask",
                "template": CVTemplate().model_dump(),
                "summary":  None,
                "response": None,
            }
            logger.info(f"[process_message] initialized new template")

        try:
            current_temp = state.get('template', {})

            # logger
            temp_to_log = current_temp.model_dump() if hasattr(current_temp, "model_dump") else current_temp
            logger.info(f"[process_message] invoking main_graph with template:\n{json.dumps(temp_to_log, indent=4, ensure_ascii=False)}")


            result = await self.graph.ainvoke(state, config)

            response_text = result.get("response") or "ngại quá không biết nói gì"

            logger.info(f"[process_message] graph done | intent={result.get('intent')} | response_text='{response_text[:50]}...'")

            result_template = result.get("template", {})

            # logger
            if hasattr(result_template, "model_dump"):
                printable_template = result_template.model_dump()
            else:
                printable_template = result_template
            logger.info(f"[process_message] updated template:\n{json.dumps(printable_template, indent=4, ensure_ascii=False)}")


            # template_keys = CVTemplate.model_fields.keys()
            # old_val_data = state.get("template", {})
            # new_val_data = result_template

            # for field_name in template_keys:
            #     if isinstance(new_val_data, CVTemplate):
            #         new_value = getattr(new_val_data, field_name, None)
            #     else:
            #         new_value = new_val_data.get(field_name) if isinstance(new_val_data, dict) else None

            #     old_value = old_val_data.get(field_name) if isinstance(old_val_data, dict) else None

            #     if old_value != new_value:
            #         logger.info(f"[process_message] template field '{field_name}' changed:\n- CŨ : {old_value}\n- MỚI: {new_value}")

            template_keys = CVTemplate.model_fields.keys()

            # 1. Lấy dữ liệu CŨ (đã là dictionary)
            old_val_dict = state.get("template", {})

            # 2. Chuyển đổi toàn bộ dữ liệu MỚI thành dictionary (Deep dump)
            if hasattr(result_template, "model_dump"):
                new_val_dict = result_template.model_dump() # Pydantic v2
            elif hasattr(result_template, "dict"):
                new_val_dict = result_template.dict()       # Pydantic v1 (phòng hờ)
            elif isinstance(result_template, dict):
                new_val_dict = result_template
            else:
                new_val_dict = {}

            # 3. Duyệt và so sánh
            for field_name in template_keys:
                old_value = old_val_dict.get(field_name)
                new_value = new_val_dict.get(field_name)

                # Lúc này cả old_value và new_value đều là dict/list/string nguyên thủy, so sánh sẽ chuẩn xác
                if old_value != new_value:

                    # Format log cho đẹp và dễ đọc (Pretty Print)
                    old_str = json.dumps(old_value, ensure_ascii=False, indent=2) if isinstance(old_value, (dict, list)) else str(old_value)
                    new_str = json.dumps(new_value, ensure_ascii=False, indent=2) if isinstance(new_value, (dict, list)) else str(new_value)

                    logger.info(
                        f"\n[process_message] template field '{field_name}' changed:\n"
                        f"--- CŨ ---\n{old_str}\n"
                        f"--- MỚI ---\n{new_str}\n"
                        f"--------------------------------------------------"
                    )

            # --- Build response ---
            response = ChatResponse(
                response=response_text,
                intent=result.get("intent", "ask"),
                session_id=session_id,
            )
            return response

        except Exception as e:
            logger.error(f"[process_message] error: {e}", exc_info=True)
            # Fallback
            return ChatResponse(
                response=f"Lỗi hệ thống: {str(e)[:100]}",
                intent="ask",
                session_id=session_id,
            )

_service_instance = ChatService()

def get_chat_service() -> ChatService:
    return _service_instance