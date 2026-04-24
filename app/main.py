from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.chat import router as chat_router
from app.api.jobs import router as jobs_router

from app.log import get_logger, setup_logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    #  Startup
    logger.info("=== App Startup ===")
    logger.info("Server startup complete")

    yield

    #  Shutdown
    logger.info("=== App Shutdown ===")
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

app.include_router(chat_router)
app.include_router(jobs_router)

@app.get("/")
async def root():
    return {
        "name": "HCNS Recruitment Chatbot",
        "version": "1.0.0",
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
