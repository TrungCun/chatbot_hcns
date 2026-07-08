"""
File Routes - Upload CV/tài liệu ứng tuyển (multipart/form-data)
"""

from flask import Blueprint

from src.views.recruitment.file_view import RecruitmentFileView

file_bp = Blueprint("recruitment_files", __name__, url_prefix="/api/recruitment/files")


@file_bp.route("/upload", methods=["POST"])
def upload_recruitment_file():
    """POST /api/recruitment/files/upload"""
    return RecruitmentFileView.upload_file()


@file_bp.route("", methods=["GET"])
def list_recruitment_files():
    """GET /api/recruitment/files?candidate_id=<id>"""
    return RecruitmentFileView.list_files()


@file_bp.route("/download", methods=["GET"])
def download_recruitment_file():
    """GET /api/recruitment/files/download?candidate_id=<id>"""
    return RecruitmentFileView.download_file()
