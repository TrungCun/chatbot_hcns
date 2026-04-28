import json
import base64
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Form, File, UploadFile
from pydantic import ValidationError

from app.schema.chat_schema import ChatRequest, ChatResponse, HealthResponse, Attachment
from app.services.chat_services import ChatService
from app.tools.pdf_handler import process_pdf_to_text
from app.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(
    request: Request,
    message: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
) -> ChatResponse:
    try:
        logger.info(f"============START==============")

        # 1. Kiểm tra Content-Type
        content_type = request.headers.get("Content-Type", "")

        chat_request: ChatRequest

        if "multipart/form-data" in content_type:
            # Xử lý Form Data (Dành cho Postman/Upload trực tiếp)
            if not message:
                raise HTTPException(status_code=400, detail="Missing 'message' field in form data")

            attachments = []
            extracted_texts = []

            if files:
                for file in files:
                    file_content = await file.read()

                    # Nếu là file PDF, trích xuất text và lưu vào danh sách
                    if file.content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf")):
                        text = process_pdf_to_text(file_content, file.filename or "unknown.pdf")
                        extracted_texts.append(text)
                        logger.info(f"[POST /chat] PDF '{file.filename}' text extracted.")
                    else:
                        # Nếu là ảnh hoặc file khác, giữ nguyên cơ chế Attachment
                        base64_content = base64.b64encode(file_content).decode("utf-8")
                        logger.info(f"[POST /chat] Attachment '{file.filename}' received. Size: {len(file_content)/1024:.2f} KB")

                        attachments.append(Attachment(
                            filename=file.filename or "unknown",
                            content_type=file.content_type or "application/octet-stream",
                            content=base64_content
                        ))

            # Nếu có text từ PDF, cộng dồn vào message để LLM đọc
            final_message = message
            if extracted_texts:
                pdf_combined_text = "\n\n".join(extracted_texts)
                final_message = f"{message}\n\n[Tài liệu đính kèm]\n{pdf_combined_text}"

            chat_request = ChatRequest(
                message=final_message,
                session_id=session_id,
                attachments=attachments if attachments else None
            )
            logger.info(f"[POST /chat] Form-Data detected: message_length={len(final_message)}, files={len(attachments)}")

        else:
            # Xử lý JSON (Dành cho Integration/Base64)
            try:
                body = await request.json()
                chat_request = ChatRequest(**body)
                logger.info(f"[POST /chat] JSON detected: message='{chat_request.message[:50]}...'")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON or Form-Data")

        # 2. Xử lý logic qua ChatService
        response = await ChatService.process_message(chat_request)

        logger.info(f"[POST /chat] response sent | intent={response.intent}")
        return response

    except ValidationError as e:
        logger.error(f"[POST /chat] validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"[POST /chat] error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)[:100]}")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version="1.0.0")
