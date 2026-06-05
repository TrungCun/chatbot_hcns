"""
Chat Routes - Session và tin nhắn theo chiến dịch tuyển dụng
"""

from flask import Blueprint

from src.views.recruitment.chat_view import RecruitmentChatView

chat_bp = Blueprint("recruitment_chat", __name__, url_prefix="/api/recruitment/chat")


@chat_bp.route("/sessions", methods=["POST"])
def ensure_chat_session():
    """POST /api/recruitment/chat/sessions"""
    return RecruitmentChatView.ensure_session()


@chat_bp.route("/messages", methods=["POST"])
def send_chat_message():
    """POST /api/recruitment/chat/messages"""
    return RecruitmentChatView.send_message()
