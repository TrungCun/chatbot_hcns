import os
from app.config import settings
from dotenv import load_dotenv
load_dotenv()
os.environ["CUDA_VISIBLE_DEVICES"] = settings.gpu_device

_gradio_tmp = os.path.join(os.path.expanduser("~"), ".cache", "gradio_tmp")
os.makedirs(_gradio_tmp, exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = _gradio_tmp

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import gradio as gr

from app.routers.chat import router as chat_router
from app.routers.jobs import router as jobs_router
from app.model.llm import get_llm
from app.config import settings
from app.tools.redis import close_redis, init_redis
from app.application import application
from fe import demo as gradio_demo

from app.log import get_logger, setup_logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    #  Startup
    logger.info("===============================================================")
    logger.info("============== App Starting =================")

    #  Model Loading
    try:
        application.load_models()
    except Exception as e:
        logger.error(f"[LIFESPAN] Failed to load application components: {e}", exc_info=True)
        raise SystemExit(1)

    #  Health Check
    try:
        test_llm = get_llm(stream = False)
        logger.info("[LIFESPAN] Checking LLM connection...")
        response = await test_llm.ainvoke("ping", max_tokens=1)
        logger.info("[LIFESPAN] LLM Health Check successful")

        await init_redis()
        logger.info("============== App Started =================")
        logger.info("===============================================================")
    except Exception as e:
        logger.error(f"[LIFESPAN] LLM health check failed: {e}", exc_info=True)
        raise SystemExit(1)

    yield

    #  Shutdown
    await close_redis()
    application.cleanup_models()
    logger.info("============== App Shutting Down =================")
    logger.info("===============================================================")

app = FastAPI(
    title="HCNS Chatbot API",
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

# Mount Gradio UI at /ui
app = gr.mount_gradio_app(app, gradio_demo, path="/ui")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9060,
        reload=True,
        log_level="info",
    )
