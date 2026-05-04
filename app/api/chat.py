from typing import Optional
from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Depends
from omegaconf import ValidationError

from app.schema.chat_schema import ChatResponse, ChatRequest, FilePayload
from app.services.chat_services import ChatService, get_chat_service

from app.log import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
async def handle_chat(
    message: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    try:
        logger.info(f"============START CHAT==============")

        file_payloads = []
        if files:
            for file in files:
                content = await file.read()
                file_payloads.append(FilePayload(
                    filename=file.filename or "unknown",
                    content_type=file.content_type or "application/octet-stream",
                    content=content
                ))

        service_request = ChatRequest(
            message=message,
            session_id=session_id,
            files=file_payloads
        )
        return await service.process_message(service_request)

    except ValidationError as e:
            logger.error(f"[POST /chat] validation error từ Service: {e}")
            raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"[POST /chat] error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)[:100]}")