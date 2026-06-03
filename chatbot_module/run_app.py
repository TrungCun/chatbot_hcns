import os
from dotenv import load_dotenv
load_dotenv()

from bot_app.config import settings
os.environ["CUDA_VISIBLE_DEVICES"] = str(settings.gpu_device)

_gradio_tmp = os.path.join(os.path.expanduser("~"), ".cache", "gradio_tmp")
os.makedirs(_gradio_tmp, exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = _gradio_tmp

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import gradio as gr

from bot_app.routers.chat import router as chat_router
from bot_app.routers.jobs import router as jobs_router
from bot_app.model.llm import get_llm
from bot_app.config import settings
from bot_app.tools.redis import close_redis, init_redis
from bot_app.tools.mysql import close_mysql, init_mysql
from bot_app.application import application
from front_end.main import demo as gradio_demo, css_content
from bot_app.log import get_logger, setup_logging
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
        init_mysql()
        logger.info("============== App Started =================")
        logger.info("===============================================================")
    except Exception as e:
        logger.error(f"[LIFESPAN] LLM health check failed: {e}", exc_info=True)
        raise SystemExit(1)

    yield

    #  Shutdown
    await close_redis()
    close_mysql()
    application.cleanup_models()
    logger.info("============== App Shutting Down =================")
    logger.info("===============================================================")

fastapi_app = FastAPI(
    title="HCNS Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(
    chat_router
)
fastapi_app.include_router(
    jobs_router
)

# Mount Gradio UI at /ui
fastapi_app = gr.mount_gradio_app(
    fastapi_app,
    gradio_demo,
    path="/ui",
    theme=gr.themes.Default(),
    head=f"<style>{css_content}</style>"
)

app = fastapi_app

if __name__ == "__main__":
    uvicorn.run(
        "run_app:app",  # Lưu ý ở đây là "run_app:app" thay vì "main:app" vì chúng ta đặt trong file run_app.py
        host="0.0.0.0",
        port=9080,
        reload=True,
        log_level="info",
    )
