import json
import os
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import func

from chatbot_module.bot_app.schema.chat_schema import FilePayload
from src.extensions import db
from src.models.recruitment.recruitment_campaign import (
    RecruitmentCandidate,
    RecruitmentCandidateCV,
)
from src.models.recruitment.recruitment_chat_message import RecruitmentChatMessage
from src.models.recruitment.recruitment_chat_session import RecruitmentChatSession
from src.views.recruitment.chat_view import (
    ROLE_ASSISTANT,
    ROLE_USER,
    _build_chatbot_params,
    _get_or_create_candidate_campaign,
    _message_to_ui,
    _next_sequence_no,
    _normalize_candidate_payload,
    _resolve_campaign_id,
)

MSG_TYPE_FILE_UPLOAD = 3
DEFAULT_UPLOAD_MESSAGE = (
    "Ứng viên vừa gửi CV. Hãy đọc và tóm tắt thông tin liên quan, "
    "đồng thời hướng dẫn các bước tiếp theo."
)
DEFAULT_AI_REPLY = (
    "Mình đã nhận CV của bạn. Bộ phận tuyển dụng sẽ xem xét và phản hồi "
    "trong cuộc trò chuyện này."
)

MAX_FILE_BYTES = int(os.environ.get("RECRUITMENT_MAX_FILE_BYTES", 10 * 1024 * 1024))
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
DEFAULT_CV_SOURCE_ID = int(os.environ.get("DEFAULT_CV_SOURCE_ID", "1"))


def _parse_bool(value, default=True):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _allowed_file(filename):
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in ALLOWED_EXTENSIONS


def _parse_candidate_json():
    raw = request.form.get("candidate")
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return _normalize_candidate_payload(data if isinstance(data, dict) else None)
    except (json.JSONDecodeError, TypeError):
        return None


def _resolve_source_id():
    source_id = request.form.get("source_id", type=int)
    return source_id if source_id else DEFAULT_CV_SOURCE_ID


def _get_or_create_candidate(db_session, candidate_data, source_id=None):
    email = candidate_data["email"]
    candidate = (
        db_session.query(RecruitmentCandidate)
        .filter(func.lower(RecruitmentCandidate.email) == email)
        .first()
    )
    now = int(datetime.now().timestamp())
    if candidate:
        candidate.name = candidate_data["fullName"]
        candidate.phone = candidate_data["phone"]
        candidate.updated_at = now
        if source_id is not None:
            candidate.source_id = source_id
        return candidate

    candidate = RecruitmentCandidate(
        name=candidate_data["fullName"],
        email=email,
        phone=candidate_data["phone"],
        source_id=source_id,
    )
    db_session.add(candidate)
    db_session.flush()
    return candidate


def _campaign_id_from_request():
    try:
        return _resolve_campaign_id(
            campaign_id=request.form.get("campaign_id"),
            session=request.form.get("session"),
        )
    except (TypeError, ValueError):
        return None


def _resolve_candidate_on_cv_submit(db_session):
    """
    Nộp CV: chỉ lưu recruitment_candidates.
    Trả về (candidate, None) hoặc (None, error_tuple).
    """
    candidate_data = _parse_candidate_json()
    source_id = _resolve_source_id()

    if candidate_data:
        candidate = _get_or_create_candidate(
            db_session, candidate_data, source_id=source_id
        )
        return candidate, None

    candidate_id = request.form.get("candidate_id", type=int)
    if candidate_id:
        candidate = (
            db_session.query(RecruitmentCandidate)
            .filter(RecruitmentCandidate.id == candidate_id)
            .first()
        )
        if not candidate:
            return None, ("Candidate not found", 404)
        candidate.source_id = source_id
        candidate.updated_at = int(datetime.now().timestamp())
        return candidate, None

    return None, (
        "candidate (JSON: fullName, email, phone) is required when submitting CV",
        400,
    )


def _candidate_data_from_db(candidate):
    return {
        "fullName": candidate.name or "",
        "email": (candidate.email or "").strip().lower(),
        "phone": candidate.phone or "",
    }


def _build_ai_context(db_session, candidate, campaign_id):
    candidate_data = _candidate_data_from_db(candidate)
    form_candidate = _parse_candidate_json()
    if form_candidate:
        if form_candidate.get("fullName"):
            candidate_data["fullName"] = form_candidate["fullName"]
        if form_candidate.get("email"):
            candidate_data["email"] = form_candidate["email"]
        if form_candidate.get("phone"):
            candidate_data["phone"] = form_candidate["phone"]

    user_id = (request.form.get("user_id") or "").strip() or None
    if not user_id and candidate_data.get("phone"):
        user_id = candidate_data["phone"].strip()

    params = _build_chatbot_params(
        db_session,
        campaign_id,
        candidate_data,
        user_id=user_id,
        session=campaign_id,
        job_context=request.form.get("job_context"),
    )
    return {**params, "candidate": candidate}


def _call_chatbot_for_upload(
    content, original_filename, content_type, candidate, campaign_id, db_session
):
    ctx = _build_ai_context(db_session, candidate, campaign_id)
    message = (request.form.get("message") or "").strip() or DEFAULT_UPLOAD_MESSAGE
    file_payload = FilePayload(
        filename=original_filename,
        content_type=content_type or "application/octet-stream",
        content=content,
    )
    ai_meta = {
        "user_id": ctx["user_id"],
        "session_id": ctx["session_id"],
        "session": ctx["campaign_id"],
        "job_context": ctx["job_context"],
    }
    try:
        from chatbot_module.chatbot_interface import get_chatbot_result

        result = get_chatbot_result(
            user_id=ctx["user_id"],
            session_id=ctx["session_id"],
            message=message,
            user_info=ctx["user_info"],
            job_context=ctx["job_context"],
            files=[file_payload],
        )
        ai_text = (result.response or "").strip() or DEFAULT_AI_REPLY
        file_urls = list(result.file_urls or [])
        return ai_text, ai_meta, file_urls
    except RuntimeError as e:
        print(f"[RecruitmentFileView] Chatbot chưa khởi tạo: {e}")
        return DEFAULT_AI_REPLY, ai_meta, []
    except Exception as e:
        print(f"[RecruitmentFileView] Lỗi khi gọi chatbot_interface: {e}")
        return DEFAULT_AI_REPLY, ai_meta, []


def _pick_ai_saved_path(file_urls):
    for path in file_urls:
        if path and os.path.isfile(path):
            return path.replace(os.sep, "/")
    for path in file_urls:
        if path:
            return str(path).replace(os.sep, "/")
    return None


def _remove_cv_file_on_disk(cv_path):
    """Xóa file CV cũ trên đĩa trước khi ghi đè bản ghi mới."""
    if not cv_path:
        return
    path = str(cv_path).strip()
    if not path or not os.path.isfile(path):
        return
    try:
        os.remove(path)
    except OSError as exc:
        print(f"[RecruitmentFileView] Không xóa được file CV cũ {path}: {exc}")


def _save_candidate_cv_from_ai_path(db_session, candidate_id, original_filename, ai_file_path):
    """Ghi DB — mỗi ứng viên một bản ghi CV; upload lại thì ghi đè và xóa file cũ."""
    now = int(datetime.now().timestamp())
    normalized_path = str(ai_file_path).replace(os.sep, "/")
    cv_file_name = os.path.basename(normalized_path)
    existing = (
        db_session.query(RecruitmentCandidateCV)
        .filter(RecruitmentCandidateCV.candidate_id == candidate_id)
        .first()
    )
    if existing:
        old_path = (existing.cv_path or "").strip().replace(os.sep, "/")
        if old_path and old_path != normalized_path:
            _remove_cv_file_on_disk(old_path)
        existing.cv_file = cv_file_name
        existing.cv_path = normalized_path
        existing.original_name = original_filename
        existing.is_primary = True
        existing.uploaded_at = now
        return existing

    record = RecruitmentCandidateCV(
        candidate_id=candidate_id,
        cv_file=cv_file_name,
        cv_path=normalized_path,
        original_name=original_filename,
        is_primary=True,
    )
    db_session.add(record)
    db_session.flush()
    return record


def _persist_upload_chat(db_session, candidate, cv_record, user_message, ai_response):
    session_token = (request.form.get("session_token") or "").strip()
    if not session_token:
        return []

    chat_session = (
        db_session.query(RecruitmentChatSession)
        .filter(RecruitmentChatSession.session_token == session_token)
        .first()
    )
    if not chat_session:
        return []

    chat_session.candidate_id = candidate.id

    user_content = user_message or f"Đã gửi file: {cv_record.original_name}"
    user_seq = _next_sequence_no(db_session, chat_session.id)
    user_msg = RecruitmentChatMessage(
        session_id=chat_session.id,
        role=ROLE_USER,
        content=user_content,
        message_type=MSG_TYPE_FILE_UPLOAD,
        sequence_no=user_seq,
        payload=json.dumps(
            {
                "cv_id": cv_record.id,
                "candidate_id": candidate.id,
                "original_filename": cv_record.original_name,
                "cv_path": cv_record.cv_path,
            },
            ensure_ascii=False,
        ),
    )
    db_session.add(user_msg)
    db_session.flush()

    bot_msg = RecruitmentChatMessage(
        session_id=chat_session.id,
        role=ROLE_ASSISTANT,
        content=ai_response,
        message_type=MSG_TYPE_FILE_UPLOAD,
        sequence_no=user_seq + 1,
    )
    db_session.add(bot_msg)
    chat_session.updated_at = int(datetime.now().timestamp())
    return [_message_to_ui(user_msg), _message_to_ui(bot_msg)]


class RecruitmentFileView:
    @staticmethod
    def upload_file():
        """
        POST /api/recruitment/files/upload
        Content-Type: multipart/form-data

        Nộp CV — ghi recruitment_candidates + recruitment_candidate_cvs.
        Nộp lại: cập nhật một bản ghi CV, xóa file cũ trên đĩa nếu có đường dẫn khác.

        Form fields:
        - file (required)
        - candidate (JSON): fullName, email, phone (bắt buộc lần đầu)
        - session / campaign_id (bắt buộc — context AI / chiến dịch)
        - candidate_id (optional — nộp lại CV khi đã có ứng viên)
        - source_id (optional, default DEFAULT_CV_SOURCE_ID)
        - user_id, job_context, session_token, message, is_cv
        """
        db_session = db.session()
        try:
            uploaded = request.files.get("file")
            if not uploaded or not uploaded.filename:
                return jsonify({"success": False, "error": "file is required"}), 400

            original_filename = uploaded.filename
            if not _allowed_file(original_filename):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Chỉ chấp nhận file PDF, DOC, DOCX",
                        }
                    ),
                    400,
                )

            content = uploaded.read()
            if not content:
                return jsonify({"success": False, "error": "File rỗng"}), 400
            if len(content) > MAX_FILE_BYTES:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"File vượt quá {MAX_FILE_BYTES // (1024 * 1024)}MB",
                        }
                    ),
                    400,
                )

            is_cv = _parse_bool(request.form.get("is_cv"), default=True)
            if not is_cv:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Chỉ hỗ trợ upload CV (is_cv=true)",
                        }
                    ),
                    400,
                )

            campaign_id = _campaign_id_from_request()
            if not campaign_id:
                db_session.close()
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "session or campaign_id is required",
                        }
                    ),
                    400,
                )

            candidate, error = _resolve_candidate_on_cv_submit(db_session)
            if error:
                message, status = error
                db_session.close()
                return jsonify({"success": False, "error": message}), status

            user_message = (request.form.get("message") or "").strip()
            ai_response, ai_meta, file_urls = _call_chatbot_for_upload(
                content,
                original_filename,
                uploaded.mimetype,
                candidate,
                campaign_id,
                db_session,
            )

            ai_file_path = _pick_ai_saved_path(file_urls)
            if not ai_file_path:
                db_session.rollback()
                db_session.close()
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "AI chưa lưu được file CV. Vui lòng thử lại.",
                        }
                    ),
                    500,
                )

            cv_record = _save_candidate_cv_from_ai_path(
                db_session,
                candidate.id,
                original_filename,
                ai_file_path,
            )
            _get_or_create_candidate_campaign(
                db_session, candidate.id, int(campaign_id)
            )
            chat_messages = _persist_upload_chat(
                db_session,
                candidate,
                cv_record,
                user_message,
                ai_response,
            )

            cv_data = cv_record.to_dict()
            candidate_data = candidate.to_dict()
            submitted_at = cv_record.uploaded_at

            db_session.commit()
            db_session.close()

            payload = {
                "success": True,
                "data": cv_data,
                "cv": cv_data,
                "candidate": candidate_data,
                "campaign_id": campaign_id,
                "submitted_at": submitted_at,
                "ai_response": ai_response,
                "messages": chat_messages,
            }
            if ai_meta:
                payload["ai_context"] = ai_meta
            payload["file_urls"] = file_urls
            return jsonify(payload), 201

        except Exception as e:
            db_session.rollback()
            db_session.close()
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def list_files():
        """GET /api/recruitment/files?candidate_id=<id>"""
        candidate_id = request.args.get("candidate_id", type=int)

        if not candidate_id:
            return (
                jsonify({"success": False, "error": "candidate_id is required"}),
                400,
            )

        try:
            db_session = db.session()
            cv = (
                db_session.query(RecruitmentCandidateCV)
                .filter(RecruitmentCandidateCV.candidate_id == candidate_id)
                .first()
            )
            data = [cv.to_dict()] if cv else []
            db_session.close()
            return jsonify({"success": True, "data": data}), 200

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
