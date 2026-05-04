import json
from langchain_core.output_parsers import StrOutputParser

from app.schema.summary_schema import CVTemplate, ProfessionalEvidence
from app.graph.summary.state import SummaryState
from app.prompt.loader import load_prompt
from app.model.llm import llm
from app.tools.multimodal import get_multimodal_messages

from app.log import get_logger
logger = get_logger(__name__)

async def extract_info(state: SummaryState) -> dict:
    logger.info(f"[extract_info] extracting information from message, attachments={len(state.get('attachments', [])) if state.get('attachments') else 0}")

    prompt = load_prompt("summary/extract_info")

    formatted_prompt = prompt.format(message=state.get("message", ""))

    messages = get_multimodal_messages(formatted_prompt, state.get("attachments"))


    response = await llm.ainvoke(messages)
    result = response.content

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


    def merge_attributes(target_obj, source_dict):
        for k, v in source_dict.items():
            if not v or not hasattr(target_obj, k):
                continue

            current_val = getattr(target_obj, k)

            # Xử lý nếu trường đó là List (ví dụ: core_skills, languages)
            if isinstance(current_val, list) and isinstance(v, list):
                # Nối danh sách và loại bỏ các phần tử trùng lặp
                new_list = current_val.copy()
                for item in v:
                    if item not in new_list:
                        new_list.append(item)
                setattr(target_obj, k, new_list)
            else:
                # Xử lý chuỗi hoặc các giá trị đơn (ghi đè an toàn vì đã check if v)
                setattr(target_obj, k, v)

    # 1. Update Candidate Overview
    if parsed_info.get("candidate_overview"):
        merge_attributes(current_template.candidate_overview, parsed_info["candidate_overview"])

    # 2. Update Education & Languages
    if parsed_info.get("education_and_languages"):
        merge_attributes(current_template.education_and_languages, parsed_info["education_and_languages"])

    # 3. Update Competency Framework
    if parsed_info.get("competency_framework"):
        merge_attributes(current_template.competency_framework, parsed_info["competency_framework"])

    if parsed_info.get("professional_evidence") and isinstance(parsed_info["professional_evidence"], list):
        for new_item in parsed_info["professional_evidence"]:
            if not isinstance(new_item, dict):
                continue

            new_entity = new_item.get("entity_name", "")
            if not new_entity:
                continue

            matched = False
            for old_ev in current_template.professional_evidence:
                old_entity = old_ev.entity_name or ""

                # Cập nhật dự án cũ nếu trùng hoặc chứa tên nhau
                if old_entity and new_entity and (old_entity.lower() in new_entity.lower() or new_entity.lower() in old_entity.lower()):
                    for key, val in new_item.items():
                        if val and hasattr(old_ev, key):
                            current_val = getattr(old_ev, key)

                            if isinstance(current_val, list) and isinstance(val, list):
                                # Gộp danh sách kỹ năng áp dụng trong dự án
                                combined_list = list(set(current_val + val))
                                setattr(old_ev, key, combined_list)
                            elif key in ["quantifiable_results", "context_and_tasks"] and current_val:
                                # Nối thêm text mô tả hoặc số liệu thay vì ghi đè
                                setattr(old_ev, key, f"{current_val}\n{val}")
                            else:
                                setattr(old_ev, key, val)
                    matched = True
                    break

            # Nếu là kinh nghiệm mới tinh -> Add nguyên block
            if not matched:
                current_template.professional_evidence.append(ProfessionalEvidence(**new_item))

    if parsed_info.get("evaluator_insights"):
        merge_attributes(current_template.evaluator_insights, parsed_info["evaluator_insights"])

    # Trả về duy nhất template đã được cập nhật an toàn
    return {
        "template": current_template
    }


def summary(state: SummaryState) -> dict:
    logger.info("[summary] evaluating template completeness")

    template_data = state.get("template")
    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        return {"evaluation": "incomplete"}

    missing = []
    # Critical: contact info to reach the candidate
    if not template.candidate_overview.contact_info:
        missing.append("contact_info")

    # Critical: at least one experience entry with meaningful description
    has_detailed_evidence = any(
        ev.context_and_tasks
        for ev in template.professional_evidence
        if isinstance(ev, ProfessionalEvidence)
    )
    if not has_detailed_evidence:
        missing.append("experience_detail")

    if missing:
        logger.info(f"[summary] incomplete - missing fields: {missing}")
        return {"evaluation": "incomplete"}

    logger.info("[summary] complete - all required fields filled")
    return {"evaluation": "complete"}


async def respond_complete(state: SummaryState) -> dict:
    logger.info("[respond_complete] finalizing process and persistent storage")
    from app.services.candidate_services import CandidateService

    template_data = state.get("template")
    summary_text_from_eval = state.get("summary", "")

    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()


    session_id = state.get("session_id", "unknown")

    # Thực hiện lưu trữ hồ sơ hoàn chỉnh (Persistent Storage)
    db_success = await CandidateService.save_profile(
        session_id=session_id,
        template=template,
        summary=summary_text_from_eval
    )
    # -------------------------

    # Tạo câu trả lời xác nhận cuối cùng dựa trên dữ liệu đã lưu
    chain = load_prompt("summary/finalize_summary") | llm | StrOutputParser()
    confirmation_response = await chain.ainvoke({"template": template.model_dump()})

    logger.info(f"[respond_complete] session_id={session_id} persist_success={db_success}")

    return {"response": confirmation_response}

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

    # Priority 1: contact info
    if not template.candidate_overview.contact_info:
        next_field = "contact_info"
    else:
        # Priority 2: detailed experience description
        has_detailed_evidence = any(
            ev.context_and_tasks
            for ev in template.professional_evidence
            if isinstance(ev, ProfessionalEvidence)
        )
        if not has_detailed_evidence:
            next_field = "experience_detail"
        else:
            next_field = "experience_detail"  # fallback

    chain = load_prompt("summary/ask_next_question") | llm | StrOutputParser()
    response = await chain.ainvoke({
        "template": template.model_dump(),
        "missing_field": next_field,
    })

    logger.info(f"[respond_incomplete] asking about field: {next_field}")
    return {"response": response}


async def evaluation(state: SummaryState) -> dict:
    logger.info("[evaluation] evaluating template and generating response")

    template_data = state.get("template")

    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()

    def merge_attributes(target_obj, source_dict):
        for k, v in source_dict.items():
            if not v or not hasattr(target_obj, k):
                continue
            current_val = getattr(target_obj, k)
            if isinstance(current_val, list) and isinstance(v, list):
                new_list = current_val.copy()
                for item in v:
                    if item not in new_list:
                        new_list.append(item)
                setattr(target_obj, k, new_list)
            else:
                setattr(target_obj, k, v)

    chain = load_prompt("summary/evaluation") | llm | StrOutputParser()
    result = await chain.ainvoke({"template": json.dumps(template.model_dump(), ensure_ascii=False)})

    try:
        parsed_eval = json.loads(result.strip())
        logger.info(f"[evaluation] parsed evaluation result")

        if "evaluator_insights" in parsed_eval:
            new_insights = parsed_eval["evaluator_insights"]
            # Lấy class EvaluatorInsights từ schema của bạn (nhớ import)
            from app.schema.summary_schema import EvaluatorInsights

            # Khởi tạo an toàn object mới từ dict trả về
            merge_attributes(template.evaluator_insights, new_insights)

        logger.info(f"[evaluation] final evaluation state updates ready")

        return {
            "template": template,
            "summary": parsed_eval.get("summary", "")
        }
    except json.JSONDecodeError as e:
        logger.error(f"[evaluation] Failed to parse JSON: {result}. Error: {e}")
        # Trả về kèm template hiện tại để luồng không bị rớt dữ liệu
        return {
            "template": template,
            "summary": "Không thể tạo đánh giá tự động tại thời điểm này do lỗi phân tích dữ liệu."
        }
