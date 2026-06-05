import json
import secrets
import os
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import desc, func
import requests

from src.extensions import db
from environment import DEFAULT_CHAT_SOURCE_ID
from src.models.recruitment.recruitment_campaign import (
    RecruitmentCampaign,
    RecruitmentCandidate,
    RecruitmentCandidateCampaign,
    RecruitmentCandidateCV,
)
from src.models.recruitment.recruitment_chat_message import RecruitmentChatMessage
from src.models.recruitment.recruitment_chat_session import RecruitmentChatSession

ROLE_USER = 1
ROLE_ASSISTANT = 2
MSG_TYPE_TEXT = 1
MSG_TYPE_JD = 5
SESSION_STATUS_ACTIVE = 1
AI_CHAT_ENDPOINT = os.environ.get("AI_CHAT_ENDPOINT", "http://127.0.0.1:9080/api/chat/")


def _normalize_candidate_payload(data):
    if not data or not isinstance(data, dict):
        return None

    full_name = (data.get("fullName") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()

    if not full_name or not email or not phone:
        return None

    return {"fullName": full_name, "email": email, "phone": phone}


def _resolve_session_source_id(body=None):
    """source_id mặc định khi đăng ký session; body có thể ghi đè."""
    body = body or {}
    raw = body.get("source_id")
    if raw is not None and str(raw).strip() != "":
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return DEFAULT_CHAT_SOURCE_ID


def _candidate_has_cv_record(session, candidate_id=None, email=None):
    """Mỗi ứng viên chỉ có tối đa một bản ghi recruitment_candidate_cvs."""
    candidate = None
    if candidate_id:
        candidate = (
            session.query(RecruitmentCandidate)
            .filter(RecruitmentCandidate.id == int(candidate_id))
            .first()
        )
    elif email:
        candidate = (
            session.query(RecruitmentCandidate)
            .filter(func.lower(RecruitmentCandidate.email) == email.strip().lower())
            .first()
        )
    if not candidate:
        return False, None

    cv = (
        session.query(RecruitmentCandidateCV)
        .filter(RecruitmentCandidateCV.candidate_id == candidate.id)
        .first()
    )
    return cv is not None, cv


def _get_or_create_candidate(
    session, candidate_data, source_id=DEFAULT_CHAT_SOURCE_ID
):
    email = candidate_data["email"]
    candidate = (
        session.query(RecruitmentCandidate)
        .filter(func.lower(RecruitmentCandidate.email) == email)
        .first()
    )

    if candidate:
        candidate.name = candidate_data["fullName"]
        candidate.phone = candidate_data["phone"]
        candidate.updated_at = int(datetime.now().timestamp())
        if source_id is not None:
            candidate.source_id = source_id
        return candidate

    candidate = RecruitmentCandidate(
        name=candidate_data["fullName"],
        email=email,
        phone=candidate_data["phone"],
        source_id=source_id,
    )
    session.add(candidate)
    session.flush()
    return candidate


def _parse_context_candidate(context_data):
    if not context_data:
        return None
    try:
        payload = (
            json.loads(context_data)
            if isinstance(context_data, str)
            else context_data
        )
        if not isinstance(payload, dict):
            return None
        return _normalize_candidate_payload(payload.get("candidate"))
    except (json.JSONDecodeError, TypeError):
        return None


def _session_context_matches_candidate(chat_session, candidate_data):
    ctx = _parse_context_candidate(chat_session.context_data)
    if not ctx or not candidate_data:
        return False
    return ctx["email"] == candidate_data["email"]


def _get_or_create_active_session(session, campaign_id, candidate_id, user_agent=None):
    chat_session = (
        session.query(RecruitmentChatSession)
        .filter(
            RecruitmentChatSession.campaign_id == campaign_id,
            RecruitmentChatSession.candidate_id == candidate_id,
            RecruitmentChatSession.status == SESSION_STATUS_ACTIVE,
        )
        .order_by(desc(RecruitmentChatSession.created_at))
        .first()
    )

    if chat_session:
        return chat_session

    chat_session = RecruitmentChatSession(
        campaign_id=campaign_id,
        candidate_id=candidate_id,
        session_token=secrets.token_urlsafe(32),
        status=SESSION_STATUS_ACTIVE,
        user_agent=(user_agent or "")[:1000] or None,
    )
    session.add(chat_session)
    session.flush()
    return chat_session


def _find_guest_active_session(session, campaign_id, candidate_data):
    """Phiên chat chưa gắn recruitment_candidates (chưa nộp CV)."""
    email = candidate_data["email"]
    rows = (
        session.query(RecruitmentChatSession)
        .filter(
            RecruitmentChatSession.campaign_id == campaign_id,
            RecruitmentChatSession.candidate_id.is_(None),
            RecruitmentChatSession.status == SESSION_STATUS_ACTIVE,
        )
        .order_by(desc(RecruitmentChatSession.created_at))
        .all()
    )
    for chat_session in rows:
        ctx = _parse_context_candidate(chat_session.context_data)
        if ctx and ctx["email"] == email:
            return chat_session
    return None


def _get_or_create_chat_session(
    session,
    campaign_id,
    candidate_data,
    session_token=None,
    user_agent=None,
):
    """
    Tạo/khôi phục phiên chat. Chưa nộp CV thì candidate_id=NULL;
    sau nộp CV, phiên gắn candidate_id thật.
    """
    token = (session_token or "").strip()
    if token:
        chat_session = (
            session.query(RecruitmentChatSession)
            .filter(RecruitmentChatSession.session_token == token)
            .first()
        )
        if (
            chat_session
            and chat_session.campaign_id == int(campaign_id)
            and chat_session.status == SESSION_STATUS_ACTIVE
            and _session_context_matches_candidate(chat_session, candidate_data)
        ):
            return chat_session

    if not token:
        guest = _find_guest_active_session(session, int(campaign_id), candidate_data)
        if guest:
            return guest

    linked = (
        session.query(RecruitmentCandidate)
        .filter(func.lower(RecruitmentCandidate.email) == candidate_data["email"])
        .first()
    )
    if linked:
        existing = _get_or_create_active_session(
            session, int(campaign_id), linked.id, user_agent
        )
        if _session_context_matches_candidate(existing, candidate_data) or not (
            existing.context_data or ""
        ).strip():
            return existing

    chat_session = RecruitmentChatSession(
        campaign_id=int(campaign_id),
        candidate_id=None,
        session_token=secrets.token_urlsafe(32),
        status=SESSION_STATUS_ACTIVE,
        user_agent=(user_agent or "")[:1000] or None,
    )
    session.add(chat_session)
    session.flush()
    return chat_session


def _get_or_create_candidate_campaign(session, candidate_id, campaign_id):
    record = (
        session.query(RecruitmentCandidateCampaign)
        .filter(
            RecruitmentCandidateCampaign.candidate_id == candidate_id,
            RecruitmentCandidateCampaign.campaign_id == campaign_id,
        )
        .first()
    )
    if record:
        record.updated_at = int(datetime.now().timestamp())
        return record

    record = RecruitmentCandidateCampaign(
        candidate_id=candidate_id,
        campaign_id=campaign_id,
    )
    session.add(record)
    session.flush()
    return record


def _next_sequence_no(session, session_id):
    last_seq = (
        session.query(func.max(RecruitmentChatMessage.sequence_no))
        .filter(RecruitmentChatMessage.session_id == session_id)
        .scalar()
    )
    return (last_seq or 0) + 1


def _message_to_ui(message):
    role_map = {ROLE_USER: "user", ROLE_ASSISTANT: "bot"}
    item = {
        "id": message.id,
        "from": role_map.get(message.role, "bot"),
        "text": message.content,
    }
    if message.message_type == MSG_TYPE_JD:
        item["type"] = "jd"
    return item


def _default_bot_reply():
    return (
        "Mình đã ghi nhận câu hỏi của bạn, bộ phận tuyển dụng sẽ phản hồi "
        "chi tiết trong cuộc trò chuyện này."
    )


def _resolve_campaign_id(campaign_id=None, session=None):
    """
    Lấy campaign_id thực từ request.
    FE gửi session dạng {sdt}_{campaignId} cho AI; campaign_id là field riêng.
    """
    if campaign_id is not None and str(campaign_id).strip() != "":
        return int(campaign_id)

    raw = ("" if session is None else str(session)).strip()
    if not raw:
        raise ValueError("campaign_id is required")

    if "_" in raw:
        return int(raw.rsplit("_", 1)[-1])

    return int(raw)


def _build_job_context_from_campaign(db_session, campaign_id, override=None):
    if override is not None and str(override).strip():
        return str(override).strip()

    campaign = (
        db_session.query(RecruitmentCampaign)
        .filter(RecruitmentCampaign.id == int(campaign_id))
        .first()
    )
    if not campaign:
        return None

    parts = []
    if campaign.name:
        parts.append(f"Vị trí: {campaign.name}")
    if campaign.jd_salary_range:
        parts.append(f"Mức lương: {campaign.jd_salary_range}")
    if campaign.jd_job_description:
        parts.append(f"Mô tả công việc:\n{campaign.jd_job_description}")
    if campaign.jd_competency_requirements:
        parts.append(f"Yêu cầu năng lực:\n{campaign.jd_competency_requirements}")
    if campaign.jd_benefits:
        parts.append(f"Phúc lợi:\n{campaign.jd_benefits}")
    return "\n".join(parts) if parts else None


def _build_chatbot_params(
    db_session,
    campaign_id,
    candidate_data,
    user_id=None,
    session=None,
    job_context=None,
):
    """
    Chuẩn hóa tham số gọi AI (giống front_end):
    - user_id: định danh ứng viên (thường là SĐT hoặc email)
    - session: campaign_id
    - session_id gửi service: {user_id}_{campaign_id}
    """
    cid = _resolve_campaign_id(campaign_id, session)
    uid = (user_id or candidate_data.get("email") or "anonymous").strip().lower()
    ai_session_id = f"{uid}_{cid}"
    user_info = json.dumps(candidate_data, ensure_ascii=False)
    ctx = _build_job_context_from_campaign(db_session, cid, job_context)
    return {
        "user_id": uid,
        "session_id": ai_session_id,
        "user_info": user_info,
        "job_context": ctx,
        "campaign_id": cid,
    }


def _call_ai_chatbot(
    campaign_id,
    candidate_data,
    content,
    user_id=None,
    session=None,
    job_context=None,
    db_session=None,
):
    """
    Gọi API chatbot AI thật để lấy phản hồi.
    API đích có thể cấu hình qua env AI_CHAT_ENDPOINT.
    """
    try:
        sql_session = db_session or db.session()
        params = _build_chatbot_params(
            sql_session,
            campaign_id,
            candidate_data,
            user_id=user_id,
            session=session,
            job_context=job_context,
        )

        from chatbot_module.chatbot_interface import get_chatbot_response

        ai_text = get_chatbot_response(
            user_id=params["user_id"],
            session_id=params["session_id"],
            message=content,
            user_info=params["user_info"],
            job_context=params["job_context"],
        )
        return ai_text or _default_bot_reply()

    except Exception as e:
        print(f"Lỗi khi gọi chatbot_interface: {e}")
        return _default_bot_reply()


class RecruitmentChatView:
    @staticmethod
    def ensure_session():
        """
        POST /api/recruitment/chat/sessions
        Body: {
          campaign_id,
          candidate: { fullName, email, phone },
          source_id (optional, mặc định DEFAULT_CHAT_SOURCE_ID=10)
        }
        Chỉ tạo/khôi phục recruitment_chat_sessions; lưu thông tin ứng viên
        tạm trong context_data. recruitment_candidates chỉ ghi khi nộp CV.
        """
        try:
            body = request.get_json(silent=True) or {}
            campaign_id = body.get("campaign_id")
            candidate_data = _normalize_candidate_payload(body.get("candidate"))
            source_id = _resolve_session_source_id(body)

            if not campaign_id:
                return (
                    jsonify({"success": False, "error": "campaign_id is required"}),
                    400,
                )

            if not candidate_data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "candidate.fullName, candidate.email and candidate.phone are required",
                        }
                    ),
                    400,
                )

            session = db.session()

            campaign = (
                session.query(RecruitmentCampaign)
                .filter(RecruitmentCampaign.id == int(campaign_id))
                .first()
            )
            if not campaign:
                session.close()
                return jsonify({"success": False, "error": "Campaign not found"}), 404

            session_token = (body.get("session_token") or "").strip()
            chat_session = _get_or_create_chat_session(
                session,
                int(campaign_id),
                candidate_data,
                session_token=session_token or None,
                user_agent=request.headers.get("User-Agent"),
            )

            chat_session.context_data = json.dumps(
                {
                    "candidate": candidate_data,
                    "campaign_id": int(campaign_id),
                    "source_id": source_id,
                },
                ensure_ascii=False,
            )
            chat_session.updated_at = int(datetime.now().timestamp())

            db_messages = (
                session.query(RecruitmentChatMessage)
                .filter(RecruitmentChatMessage.session_id == chat_session.id)
                .order_by(
                    RecruitmentChatMessage.sequence_no.asc(),
                    RecruitmentChatMessage.id.asc(),
                )
                .all()
            )

            candidate_payload = None
            candidate_campaign_payload = None
            if chat_session.candidate_id:
                candidate = (
                    session.query(RecruitmentCandidate)
                    .filter(RecruitmentCandidate.id == chat_session.candidate_id)
                    .first()
                )
                if candidate:
                    candidate_payload = candidate.to_dict()
                    cc = (
                        session.query(RecruitmentCandidateCampaign)
                        .filter(
                            RecruitmentCandidateCampaign.candidate_id
                            == candidate.id,
                            RecruitmentCandidateCampaign.campaign_id
                            == int(campaign_id),
                        )
                        .first()
                    )
                    if cc:
                        candidate_campaign_payload = cc.to_dict()

            has_cv, cv_record = _candidate_has_cv_record(
                session,
                candidate_id=chat_session.candidate_id,
                email=candidate_data["email"],
            )

            session.commit()

            response_data = {
                "session": chat_session.to_dict(),
                "candidate": candidate_payload,
                "candidate_campaign": candidate_campaign_payload,
                "messages": [_message_to_ui(item) for item in db_messages],
                "has_cv": has_cv,
            }
            if cv_record:
                response_data["cv"] = cv_record.to_dict()
            session.close()
            return jsonify({"success": True, "data": response_data}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def send_message():
        """
        POST /api/recruitment/chat/messages
        Body: {
          session_token,
          campaign_id,
          candidate: { fullName, email, phone },
          content,
          source_id (optional, mặc định DEFAULT_CHAT_SOURCE_ID=10),
          user_id (str, optional),
          session (int, campaign_id — ưu tiên hơn campaign_id nếu gửi),
          job_context (str, optional)
        }
        """
        try:
            body = request.get_json(silent=True) or {}
            session_token = (body.get("session_token") or "").strip()
            campaign_id = body.get("campaign_id")
            content = (body.get("content") or "").strip()
            candidate_data = _normalize_candidate_payload(body.get("candidate"))

            if not session_token:
                return (
                    jsonify({"success": False, "error": "session_token is required"}),
                    400,
                )
            if not campaign_id:
                return (
                    jsonify({"success": False, "error": "campaign_id is required"}),
                    400,
                )
            if not content:
                return (
                    jsonify({"success": False, "error": "content is required"}),
                    400,
                )
            if not candidate_data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "candidate.fullName, candidate.email and candidate.phone are required",
                        }
                    ),
                    400,
                )

            source_id = _resolve_session_source_id(body)
            session = db.session()

            chat_session = (
                session.query(RecruitmentChatSession)
                .filter(RecruitmentChatSession.session_token == session_token)
                .first()
            )
            if not chat_session:
                session.close()
                return jsonify({"success": False, "error": "Session not found"}), 404

            if chat_session.campaign_id != int(campaign_id):
                session.close()
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Session does not belong to this campaign",
                        }
                    ),
                    400,
                )

            if not _session_context_matches_candidate(chat_session, candidate_data):
                session.close()
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Session does not belong to this candidate",
                        }
                    ),
                    403,
                )

            if chat_session.candidate_id is not None:
                candidate = (
                    session.query(RecruitmentCandidate)
                    .filter(RecruitmentCandidate.id == chat_session.candidate_id)
                    .first()
                )
                if not candidate:
                    session.close()
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Candidate not found for session",
                            }
                        ),
                        404,
                    )
                candidate.name = candidate_data["fullName"]
                candidate.phone = candidate_data["phone"]
                candidate.updated_at = int(datetime.now().timestamp())
                if source_id is not None:
                    candidate.source_id = source_id

            user_seq = _next_sequence_no(session, chat_session.id)
            user_message = RecruitmentChatMessage(
                session_id=chat_session.id,
                role=ROLE_USER,
                content=content,
                message_type=MSG_TYPE_TEXT,
                sequence_no=user_seq,
            )
            session.add(user_message)
            session.flush()

            bot_content = _call_ai_chatbot(
                campaign_id=campaign_id,
                candidate_data=candidate_data,
                content=content,
                user_id=body.get("user_id"),
                session=body.get("session") or campaign_id,
                job_context=body.get("job_context"),
                db_session=session,
            )
            bot_seq = user_seq + 1
            bot_message = RecruitmentChatMessage(
                session_id=chat_session.id,
                role=ROLE_ASSISTANT,
                content=bot_content,
                message_type=MSG_TYPE_TEXT,
                sequence_no=bot_seq,
            )
            session.add(bot_message)

            chat_session.updated_at = int(datetime.now().timestamp())
            chat_session.context_data = json.dumps(
                {
                    "candidate": candidate_data,
                    "campaign_id": int(campaign_id),
                    "source_id": source_id,
                },
                ensure_ascii=False,
            )

            session.commit()

            response_data = {
                "session": chat_session.to_dict(),
                "messages": [
                    _message_to_ui(user_message),
                    _message_to_ui(bot_message),
                ],
            }
            session.close()
            return jsonify({"success": True, "data": response_data}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
