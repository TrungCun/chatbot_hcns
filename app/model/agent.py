import os
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv()

from app.log import get_logger
logger = get_logger(__name__)


def get_llm(stream: bool = False) -> ChatOpenAI:
    """Khởi tạo LLM từ cấu hình trong .env, dùng OpenAI-compatible endpoint (llama.cpp).

    Tham số extra_body:
      - chat_template_kwargs.enable_thinking=False : tắt chế độ reasoning của Qwen3,
        tránh sinh ra khối <think>...</think> trong response.
      - top_p, top_k, min_p                        : kiểm soát độ đa dạng token.
    """
    return ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        api_key="not-required",  # llama.cpp không yêu cầu API key
        streaming=stream,
        top_p=0.8,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


if __name__ == "__main__":
    base_url = os.getenv("LLM_BASE_URL", "")
    model = os.getenv("LLM_MODEL", "")

    logger.info(f"LLM HEALTH CHECK | base_url={base_url} | model={model}")

    # 1. Kiểm tra server có phản hồi không
    logger.info("[1] Ping server...")
    try:
        resp = httpx.get(f"{base_url}/models", timeout=5)
        resp.raise_for_status()
        models = [m["id"] for m in resp.json().get("data", [])]
        logger.info(f"Ping OK (HTTP {resp.status_code}) | models={models}")
    except Exception as e:
        logger.error(f"Ping FAIL: {e}")
        raise SystemExit(1)

    # 2. Kiểm tra model có tồn tại trong danh sách không
    logger.info(f"[2] Kiểm tra model '{model}'...")
    if model in models:
        logger.info("Model sẵn sàng")
    else:
        logger.warning("Không tìm thấy model trong danh sách, tiếp tục thử gọi")

    # 3. Gọi thử inference
    logger.info("[3] Gọi thử inference...")
    try:
        llm = get_llm(stream=False)
        response = llm.invoke([HumanMessage(content="Trả lời đúng 1 từ: xin chào")])
        logger.info(f"Inference OK | response='{response.content.strip()}'")
    except Exception as e:
        logger.error(f"Inference FAIL: {e}")
        raise SystemExit(1)

    logger.info("KẾT QUẢ: LLM hoạt động bình thường")

