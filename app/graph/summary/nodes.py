import json
from langchain_core.output_parsers import StrOutputParser

from app.schema.summary_schema import CVTemplate
from app.graph.summary.state import SummaryState
from app.prompt.loader import load_prompt
from app.model.llm import llm

from app.log import get_logger
logger = get_logger(__name__)

async def extract_info(state: SummaryState) -> dict:
    logger.info("[extract_info] extracting information from message")
    chain = load_prompt("summary/extract_info") | llm | StrOutputParser()
    result = await chain.ainvoke({"message": state["message"]})

    try:
        parsed_info = json.loads(result.strip())
        logger.info(f"[extract_info] extracted info:\n{json.dumps(parsed_info, indent=4, ensure_ascii=False)}")
    except json.JSONDecodeError as e:
        logger.error(f"[extract_info] Failed to parse JSON: {result}. Error: {e}")
        parsed_info = {}


    current_template_data = state.get("template")
    if isinstance(current_template_data, CVTemplate):
        current_template = current_template_data
    elif isinstance(current_template_data, dict):
        current_template = CVTemplate(**current_template_data)
    else:
        current_template = CVTemplate()

    if "candidate_overview" in parsed_info and parsed_info["candidate_overview"]:
        for k, v in parsed_info["candidate_overview"].items():
            if v and hasattr(current_template.candidate_overview, k):
                setattr(current_template.candidate_overview, k, v)

    if "education_and_languages" in parsed_info and parsed_info["education_and_languages"]:
        for k, v in parsed_info["education_and_languages"].items():
            if v and hasattr(current_template.education_and_languages, k):
                setattr(current_template.education_and_languages, k, v)

    if "competency_framework" in parsed_info and parsed_info["competency_framework"]:
        for k, v in parsed_info["competency_framework"].items():
            if v and hasattr(current_template.competency_framework, k):
                setattr(current_template.competency_framework, k, v)

    if "professional_evidence" in parsed_info and isinstance(parsed_info["professional_evidence"], list):
         from app.schema.summary_schema import ProfessionalEvidence
         current_template.professional_evidence = [
             ProfessionalEvidence(**item) if isinstance(item, dict) else item
             for item in parsed_info["professional_evidence"]
         ]

    return {
        "template": current_template,
        "extracted_info": result
    }


def summary(state: SummaryState) -> dict:
    logger.info("[summary] evaluating template completeness")
    from app.schema.summary_schema import CVTemplate

    template_data = state.get("template")
    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        return {"evaluation": "incomplete"}

    missing = []
    # Check essential fields in candidate_overview
    if not template.candidate_overview.full_name:
        missing.append("họ tên")
    if not template.candidate_overview.contact_info:
        missing.append("thông tin liên hệ")

    # Check education
    if not template.education_and_languages.highest_degree:
        missing.append("bằng cấp/trình độ")

    # Check experience
    if not template.professional_evidence:
        missing.append("kinh nghiệm làm việc")

    if missing:
        logger.info(f"[summary] incomplete - missing fields: {missing}")
        return {"evaluation": "incomplete"}

    logger.info("[summary] complete - all required fields filled")
    return {"evaluation": "complete"}


async def respond_complete(state: SummaryState) -> dict:
    logger.info("[respond_complete] generating summary response")
    from app.schema.summary_schema import CVTemplate

    template_data = state.get("template")

    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()

    chain = load_prompt("summary/finalize_summary") | llm | StrOutputParser()
    # Pass model_dump for prompt context
    summary_text = await chain.ainvoke({"template": template.model_dump()})

    response = (
        f"{summary_text}\n\n"
        "Cảm ơn bạn đã cung cấp đầy đủ thông tin. "
        "Hồ sơ của bạn đã được ghi nhận thành công!"
    )
    logger.info("[respond_complete] response generated")
    return {"response": response}


async def respond_incomplete(state: SummaryState) -> dict:
    logger.info("[respond_incomplete] generating missing-info question")
    from app.schema.summary_schema import CVTemplate

    template_data = state.get("template")
    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()

    missing = []
    if not template.candidate_overview.full_name: missing.append("họ tên")
    if not template.candidate_overview.contact_info: missing.append("thông tin liên hệ (email/SĐT)")
    if not template.education_and_languages.highest_degree: missing.append("trình độ học vấn")
    if not template.professional_evidence: missing.append("mô tả kinh nghiệm/dự án")

    # Ask about the first missing field
    next_field = missing[0] if missing else "thông tin bổ sung"

    chain = load_prompt("summary/ask_next_question") | llm | StrOutputParser()
    response = await chain.ainvoke({
        "template": template.model_dump(),
        "missing_field": next_field,
    })

    logger.info(f"[respond_incomplete] asking about field: {next_field}")
    return {"response": response}


async def evaluation(state: SummaryState) -> dict:
    logger.info("[evaluation] evaluating template and generating response")
    from app.schema.summary_schema import CVTemplate

    template_data = state.get("template")

    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()

    chain = load_prompt("summary/evaluation") | llm | StrOutputParser()
    result = await chain.ainvoke({"template": json.dumps(template.model_dump(), ensure_ascii=False)})

    try:
        parsed_eval = json.loads(result.strip())
        logger.info(f"[evaluation] parsed evaluation result")

        # Chuẩn hóa dữ liệu template nếu có trong kết quả trả về
        if "template" in parsed_eval:
            from app.schema.summary_schema import CVTemplate
            # Đảm bảo dữ liệu map đúng vào model Pydantic
            if isinstance(parsed_eval["template"], dict):
                parsed_eval["template"] = CVTemplate(**parsed_eval["template"])

        logger.info(f"[evaluation] final evaluation state updates: {parsed_eval}")

        # LangGraph sẽ tự động merge các trường trong parsed_eval vào State
        return parsed_eval
    except json.JSONDecodeError as e:
        logger.error(f"[evaluation] Failed to parse JSON: {result}. Error: {e}")
        return {"summary": "Không thể tạo đánh giá tự động tại thời điểm này."}
