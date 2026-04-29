from langchain_core.messages import HumanMessage

from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

def auto_detect_vision_support() -> bool:
    test_llm = get_llm()

    tiny_pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    probe_message = [
        HumanMessage(content=[
            {"type": "text", "text": "ping"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{tiny_pixel_b64}"}
            }
        ])
    ]

    try:
        logger.info("Testing Vision LLM...")

        test_llm.invoke(probe_message, max_tokens=1)

        logger.info("SUCCESS: LLM model support Vision detected.")
        return True

    except Exception as e:
        logger.warning(f"FALLBACK: LLM rejected image input. Activating Local OCR. (Internal error code: {e})")
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys

    load_dotenv()

    from app.log import setup_logging
    setup_logging()

    logger.info("Starting Test: Detecting LLM Vision capabilities")
    logger.info("-" * 50)

    try:
        has_vision = auto_detect_vision_support()

        logger.info("-" * 50)
        if has_vision:
            logger.info("RESULT: Model SUPPORTS Vision.")
        else:
            logger.warning("RESULT: Model DOES NOT SUPPORT Vision.")

    except Exception as e:
        logger.error(f"Error during test: {e}")
        sys.exit(1)