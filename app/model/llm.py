import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv()

from app.log import get_logger
logger = get_logger(__name__)

def get_llm(stream: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        api_key="not-required",
        streaming=stream,
        top_p=0.8,
        extra_body={
            "top_k": 20,
            "min_p": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


if __name__ == "__main__":
    try:
        logger.info("LLM Health Check...")
        llm = get_llm(stream=False)
        response = llm.invoke([HumanMessage(content="OK")])
        logger.info(f"LLM is alive: {response.content.strip()}")
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        raise SystemExit(1)

