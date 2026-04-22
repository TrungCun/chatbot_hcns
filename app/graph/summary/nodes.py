import json
from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.graph.summary.state import SummaryState
from app.prompt.loader import load_prompt
from app.model.llm import get_llm

from app.log import get_logger
logger = get_logger(__name__)

def _make_llm() -> ChatOpenAI:
    return get_llm(stream=False)

async def extract_info(state: SummaryState) -> dict:
    logger.info("[extract_info] extracting information from message")
    llm = _make_llm()
    chain = load_prompt("summary/extract_info") | llm | StrOutputParser()
    result = await chain.ainvoke({"message": state["message"]})

    # Parse JSON response
    try:
        parsed_info = json.loads(result.strip())
        logger.info(f"[extract_info] extracted info={parsed_info}")
    except json.JSONDecodeError as e:
        logger.error(f"[extract_info] Failed to parse JSON: {result}. Error: {e}")
        parsed_info = {}

    # Update template by updating only specific fields with extracted values
    updated_template = state.get("template", {}).copy()

    # Only update fields that have non-null/non-empty values to avoid overwriting
    for field_name, field_value in parsed_info.items():
        if field_name in updated_template:
            # Only update if the extracted value is not null and not empty
            if field_value is not None and (not isinstance(field_value, (list, dict)) or len(field_value) > 0):
                logger.info(f"[extract_info] updating field '{field_name}' with value: {field_value}")
                updated_template[field_name] = field_value
            else:
                logger.info(f"[extract_info] skipping field '{field_name}' - empty/null value")
        else:
            logger.warning(f"[extract_info] field '{field_name}' not in template")

    return {
        "template": updated_template,
        "extracted_info": result
    }


def summary(state: SummaryState) -> dict:
    logger.info("[summary] evaluating template completeness")
    template = state.get("template", {})

    required_fields = ["name", "email", "phone", "education", "experience", "skills"]
    missing = []

    for field in required_fields:
        value = template.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)

    if missing:
        logger.info(f"[summary] incomplete - missing fields: {missing}")
        return {"evaluation": "incomplete"}

    logger.info("[summary] complete - all required fields filled")
    return {"evaluation": "complete"}


async def respond_complete(state: SummaryState) -> dict:
    logger.info("[respond_complete] generating summary response")
    llm = _make_llm()
    chain = load_prompt("summary/finalize_summary") | llm | StrOutputParser()
    summary_text = await chain.ainvoke({"template": state["template"]})

    response = (
        f"{summary_text}\n\n"
        "Cảm ơn bạn đã cung cấp đầy đủ thông tin. "
        "Hồ sơ của bạn đã được ghi nhận thành công!"
    )
    logger.info("[respond_complete] response generated")
    return {"response": response}


async def respond_incomplete(state: SummaryState) -> dict:
    logger.info("[respond_incomplete] generating missing-info question")
    template = state.get("template", {})

    required_fields = ["name", "email", "phone", "education", "experience", "skills"]
    missing = [
        field for field in required_fields
        if template.get(field) is None or template.get(field) == "" or template.get(field) == []
    ]

    # Ask about the first missing field
    next_field = missing[0] if missing else "thông tin"

    llm = _make_llm()
    chain = load_prompt("summary/ask_next_question") | llm | StrOutputParser()
    response = await chain.ainvoke({
        "template": template,
        "missing_field": next_field,
    })

    logger.info(f"[respond_incomplete] asking about field: {next_field}")
    return {"response": response}