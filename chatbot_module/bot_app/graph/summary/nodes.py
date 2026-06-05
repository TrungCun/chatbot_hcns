import json
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser

from bot_app.schema.summary_schema import CVTemplate, EvaluatorInsights
from bot_app.graph.summary.state import SummaryState
from bot_app.prompt.loader import load_prompt
from bot_app.model.llm import llm, llm_stream
from bot_app.tools.mysql import get_mysql_engine
from sqlalchemy import text

from bot_app.log import get_logger
logger = get_logger(__name__)

async def acknowledge_receipt(state: SummaryState) -> dict:
    logger.info("[acknowledge_receipt] Sending immediate acknowledgment to user.")
    response = "Đã nhận thông tin/CV của bạn. Hệ thống đang tiến hành xử lý và phân tích hồ sơ, vui lòng chờ trong giây lát (hoặc bạn có thể hỏi các câu hỏi khác trong lúc chờ)."
    return {
        "response": response,
        "history": [AIMessage(content=response)]
    }

async def extract_info(state: SummaryState) -> dict:
    logger.info(f"[EXTRACT INFO] extracting information from message, attachments={len(state.get('attachments', [])) if state.get('attachments') else 0}")

    message = state["message"]
    attachments = state.get("attachments")
    context = state.get("context") or "Chưa có bối cảnh hội thoại."
    history = state.get("history", [])
    filtered_history = [m for m in history if m.type in ["human", "ai"]]

    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            query = text("""
                SELECT DISTINCT rc.name AS position_name
                FROM recruitment_campaigns rc
                WHERE rc.status = 1
                AND (rc.end_time IS NULL OR rc.end_time >= UNIX_TIMESTAMP())
            """)
            rows = conn.execute(query).fetchall()
            job_titles = [row[0] for row in rows if row[0]]
            available_jobs_str = ", ".join(job_titles) if job_titles else "Không có vị trí mở."
    except Exception as e:
        logger.error(f"[EXTRACT INFO] Lỗi lấy job từ MySQL: {e}")
        available_jobs_str = "Không lấy được danh sách vị trí."

    try:

        prompt = load_prompt("summary/extract_info")
        chain = prompt | llm
        response = await chain.ainvoke({
            "message": message,
            "context": context,
            "history": filtered_history,
            "available_jobs": available_jobs_str
        })

        result = response.content
    except Exception as e:
        logger.error(f"[EXTRACT INFO] LLM Error: {e}")
        return {}

    # logger.info(f"[DEBUG TYPE] response is type: {type(response)} | result is type: {type(result)}")

    try:
        # convert từ str sang obj
        result_obj = CVTemplate.model_validate_json(result)
        # convert về dict, chỉ lấy những trường có dữ liệu (exclude_unset) để tránh ghi đè template bằng null hoặc empty string
        parsed_info = result_obj.model_dump(exclude_unset=True)
        logger.info(f"[EXTRACT INFO] extractedddddd info:\n{json.dumps(parsed_info, indent=4, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"[EXTRACT INFO] LLM trả về dữ liệu lỗi: {e}")
        parsed_info = {}

    logger.info(f"[EXTRACT INFO] type: {type(parsed_info)}")

    current_template = CVTemplate.model_validate(state.get("template", {}))
    logger.info(f"[EXTRACT INFO] current_template:\n{current_template.model_dump_json(indent=4)}")


    def deduplicate_list(lst):
        """Lọc trùng list không phân biệt hoa thường, giữ format của phần tử đầu tiên"""
        seen = set()
        result = []
        for item in lst:
            if isinstance(item, str):
                normalized = item.strip().lower() # Đưa về chữ thường để so sánh
                if normalized not in seen:
                    seen.add(normalized)
                    result.append(item) # Vẫn giữ lại chữ gốc (vd: "Proteus")
            else:
                result.append(item)
        return result

    def merge_template_data(current_template, parsed_info: dict):
        updated_data = current_template.model_dump()

        for section_key, new_section_value in parsed_info.items():
            if new_section_value is None:
                continue

            old_section_value = updated_data.get(section_key)

            if isinstance(new_section_value, dict):
                for field_key, new_field_value in new_section_value.items():
                    if new_field_value is not None:
                        if isinstance(new_field_value, list):
                            old_list = old_section_value.get(field_key) or []
                            updated_data[section_key][field_key] = deduplicate_list(old_list + new_field_value)
                        else:
                            updated_data[section_key][field_key] = new_field_value

            elif isinstance(new_section_value, list):
                if all(isinstance(i, str) for i in new_section_value):
                    updated_data[section_key] = deduplicate_list((old_section_value or []) + new_section_value)
                else:
                    for new_item in new_section_value:
                        entity_name = new_item.get("entity_name")
                        if not entity_name:
                            updated_data[section_key].append(new_item)
                            continue

                        match_item = next(
                            (item for item in updated_data[section_key]
                            if item.get("entity_name") == entity_name),
                            None
                        )

                        if match_item:
                            for k, v in new_item.items():
                                if v is not None:
                                    if isinstance(v, list):
                                        match_item[k] = deduplicate_list((match_item.get(k) or []) + v)
                                    else:
                                        match_item[k] = v
                        else:
                            updated_data[section_key].append(new_item)

        return current_template.model_validate(updated_data)

    current_template = merge_template_data(current_template, parsed_info)
    return {
        "template": current_template.model_dump()
    }



async def evaluation(state: SummaryState) -> dict:
    logger.info("[evaluation] Generating professional HR insights")

    template_data = state.get("template")
    if isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = template_data or CVTemplate()

    # 1. Chuẩn bị dữ liệu (Facts only)
    input_facts = {
        "candidate_overview": template.candidate_overview.model_dump(),
        "education_and_languages": template.education_and_languages.model_dump(),
        "competency_framework": template.competency_framework.model_dump(),
        "professional_evidence": [ev.model_dump() for ev in template.professional_evidence]
    }

    facts_string = json.dumps(input_facts, ensure_ascii=False, indent=2)

    chain = load_prompt("summary/evaluation") | llm | StrOutputParser()

    result = await chain.ainvoke({
        "context": f"DỮ LIỆU HỒ SƠ ỨNG VIÊN:\n{facts_string}",
        "history": [], # Không cần history cho node phân tích tĩnh này
        "message": "Dựa vào dữ liệu hồ sơ bên trên, hãy tiến hành đánh giá chuyên môn và trả về JSON theo đúng định dạng yêu cầu."
    })

    try:
        parsed_eval = json.loads(result.strip())

        # 2. Dynamic Update - Schema-Driven
        # Pydantic sẽ tự lọc các trường thừa và ép kiểu dữ liệu
        new_insights = EvaluatorInsights(**parsed_eval)
        template.evaluator_insights = new_insights

        # 3. Dọn dẹp trạng thái nợ nần
        template.missing_information = []

        logger.info(f"[evaluation] Successfully mapped insights for {template.candidate_overview.full_name}")

    except Exception as e:
        # Nếu AI trả về JSON lỗi, ta vẫn giữ nguyên Facts cũ, chỉ log lỗi
        logger.error(f"[evaluation] Mapping/Parsing error: {e}")
        # Bạn có thể gán một thông báo lỗi vào summary nếu muốn
        template.evaluator_insights.summary = "Hệ thống gặp sự cố khi phân tích đánh giá."

    # 4. QUAN TRỌNG NHẤT: Trả về để cập nhật State tổng
    return {
        "template": template.model_dump()
    }

async def respond_complete(state: SummaryState) -> dict:
    logger.info("[respond_complete] finalizing process and persistent storage")
    from bot_app.services.candidate_services import CandidateService

    template_data = state.get("template")

    if isinstance(template_data, CVTemplate):
        template = template_data
    elif isinstance(template_data, dict):
        template = CVTemplate(**template_data)
    else:
        template = CVTemplate()

    session_id = state.get("session_id", "unknown")

    # --- BƯỚC 1: TRÍCH XUẤT SUMMARY AN TOÀN CHO DATABASE ---
    summary_text_from_eval = ""
    if template.evaluator_insights and template.evaluator_insights.summary:
        summary_text_from_eval = template.evaluator_insights.summary

    # Thực hiện lưu trữ hồ sơ hoàn chỉnh (Persistent Storage)
    db_success = await CandidateService.save_profile(
        session_id=session_id,
        template=template,
        summary=summary_text_from_eval
    )
    # --------------------------------------------------------

    chain = load_prompt("summary/finalize_summary") | llm_stream | StrOutputParser()

    confirmation_response = await chain.ainvoke({
        "context": "{}", # Không cần context nữa vì prompt đã được đơn giản hóa
        "history": [],
        "message": state.get("message", "")
    })
    # --------------------------------------------------------

    logger.info(f"[respond_complete] session_id={session_id} persist_success={db_success}")

    return {
        "response": confirmation_response,
        "history": [AIMessage(content=confirmation_response)]
    }


