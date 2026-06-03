from typing import Optional
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from bot_app.schema.chat_schema import ChatResponse, ChatRequest
from bot_app.tools.helper import HelperTools
from bot_app.services.chat_services import ChatService, get_chat_service

from bot_app.log import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

async def _build_chat_request(
    user_id: Optional[str],
    session_id: Optional[str],
    user_info: Optional[str],
    job_context: Optional[str],
    message: Optional[str],
    files: Optional[list[UploadFile]],
    n8n_file_data: Optional[str] = None,
    n8n_file_name: Optional[str] = None,
    n8n_mime_type: Optional[str] = None,
) -> ChatRequest:
    # Chuẩn hóa giá trị từ n8n: nếu là "undefined" (dạng string), chuyển thành None
    message = HelperTools.sanitize_n8n_value(message)
    session_id = HelperTools.sanitize_n8n_value(session_id)
    user_id = HelperTools.sanitize_n8n_value(user_id)
    user_info = HelperTools.sanitize_n8n_value(user_info)

    # Return for case missing user_id or session_id
    if not user_id or not session_id:
        raise HTTPException(
            status_code=400,
            detail="Thiếu user_id hoặc session_id. Vui lòng cung cấp đầy đủ."
        )

    # Return for case both message and files are empty
    if not message and not files and not n8n_file_data:
        logger.warning("[CHAT BUILDER] No message or files provided in the request.")
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp ít nhất một tin nhắn hoặc một file đính kèm."
        )

    file_payloads = []
    # --- Handle standard multipart UploadFile ---
    if files:
        try:
            for file in files:
                content = await file.read()
                file_payloads.append(HelperTools.normalize_file(
                    content=content,
                    filename=file.filename,
                    content_type=file.content_type
                ))
        except Exception as e:
            logger.error(f"[CHAT BUILDER] Failed to read uploaded files: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail="Không thể đọc file đính kèm. Vui lòng thử lại với file khác.")

    # --- Handle n8n binary format (base64 in text form fields) ---
    if n8n_file_data:
        try:
            content = HelperTools.decode_n8n_base64(n8n_file_data)
            file_payloads.append(HelperTools.normalize_file(
                content=content,
                filename=n8n_file_name or "n8n_file",
                content_type=n8n_mime_type
            ))
        except Exception as e:
            logger.error(f"[CHAT BUILDER] Failed to decode n8n binary file: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail="Không thể giải mã file từ n8n. Kiểm tra lại trường n8n_file_data.")

    # Chat request object to pass to service layer
    return ChatRequest(
        user_id=user_id,
        session_id=session_id,
        user_info=user_info,
        job_context=job_context,
        message=message,
        files=file_payloads
    )

# Chat endpoint for handling N8N requests.
@router.post("/", response_model=ChatResponse)
async def handle_chat(
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_info: Optional[str] = Form(None),
    job_context: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),

    # for n8n file data
    n8n_file_data: Optional[str] = Form(None),
    n8n_file_name: Optional[str] = Form(None),
    n8n_mime_type: Optional[str] = Form(None),
    service: ChatService = Depends(get_chat_service)
):
    try:
        logger.info(f"==================START CHAT====================")
        service_request = await _build_chat_request(
            user_id, session_id, user_info, job_context, message, files,
            n8n_file_data, n8n_file_name, n8n_mime_type
        )
        return await service.process_message(service_request)

    except ValidationError as e:
        logger.error(f"[POST /chat] Pydantic validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail="Định dạng dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[POST /chat] error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)[:100]}")


# Streaming endpoint for chat responses.
@router.post("/stream")
async def handle_chat_stream(
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_info: Optional[str] = Form(None),
    job_context: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    service: ChatService = Depends(get_chat_service)
):
    try:
        logger.info(f"==================START CHAT====================")
        service_request = await _build_chat_request(
            user_id, session_id, user_info, job_context, message, files
        )

        # Streaming response from service layer, with appropriate headers for SSE
        return StreamingResponse(
            service.stream_message(service_request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[POST /chat] error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)[:100]}")
