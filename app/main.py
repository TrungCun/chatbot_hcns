from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.chat import router as chat_router
from app.api.jobs import router as jobs_router
from app.model.llm import get_llm
from app.config import settings
from app.tools.llm_checker import auto_detect_vision_support
from app.tools.redis import close_redis, init_redis
from app.log import get_logger, setup_logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    #  Startup
    logger.info("=== App Starting ===")

    #  Health Check
    try:
        test_llm = get_llm(stream = False)
        logger.info("Checking LLM connection...")
        response = test_llm.invoke("ping", max_tokens=1)
        logger.info(f"LLM Health Check successful")

        has_vision = auto_detect_vision_support()
        settings.llm_support_vision = has_vision
        logger.info(f"LLM Vision Support: {has_vision}")

        await init_redis()

    except Exception as e:
        logger.error(f"LLM health check failed: {e}", exc_info=True)
        raise SystemExit(1)


    yield

    #  Shutdown
    logger.info("=== App Shuting Down ===")
    await close_redis()
    logger.info("Server shutdown complete")



app = FastAPI(
    title="HCNS Recruitment Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router
)
app.include_router(
    jobs_router
)

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "HCNS Recruitment Chatbot",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
