from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.log import get_logger
from app.config import settings

logger = get_logger(__name__)

@lru_cache(maxsize=2)
def get_llm(stream: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key="not-required",
        streaming=stream,
        timeout=60,
        max_retries=2,
        top_p=0.8,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    )

llm = get_llm(stream=False)
llm_stream = get_llm(stream=True)

if __name__ == "__main__":
    try:
        logger.info("Bắt đầu LLM Health Check...")
        test_llm = get_llm(stream=False)
        response = test_llm.invoke([HumanMessage(content="Hello, respond with exactly 'OK'")])
        logger.info(f"LLM response: {response.content.strip()}")
    except Exception as e:
        logger.error(f"LLM health check thất bại: {e}", exc_info=True)
        raise SystemExit(1)
