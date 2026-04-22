"""
FastAPI application entry point.

Features:
  - Lifespan management: load embedding models on startup
  - Router mounting: chat API
  - CORS enabled
  - Logging configured
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from app.application import application
from app.api.chat import router as chat_router
from app.api.jobs import router as jobs_router

from app.log import get_logger, setup_logging

# Setup logging ngay khi module load
setup_logging()

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — load/unload resources.

    Startup:
      - Load embedding models (dense + sparse)

    Shutdown:
      - Cleanup models
    """
    # --- Startup ---
    logger.info("=== App Startup ===")
    logger.info("✓ Server startup complete (embedding models skipped)")

    yield

    # --- Shutdown ---
    logger.info("=== App Shutdown ===")
    logger.info("✓ Server shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HCNS Recruitment Chatbot API",
    description="Chatbot tuyển dụng với 2 flows: RAG Q&A + CV/interview collection",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict sau
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(chat_router)
app.include_router(jobs_router)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint — API info."""
    return {
        "name": "HCNS Recruitment Chatbot",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
