from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schema.chat_schema import ChatRequest, ChatResponse, HealthResponse
from app.services.chat_services import chat_message
from app.log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest) -> ChatResponse:
    try:
        logger.info(f"============START==============")
        logger.info(f"[POST /chat] message='{request.message[:50]}...'")
        response = await chat_message(request)
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
