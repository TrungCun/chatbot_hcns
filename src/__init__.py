from email.utils import unquote
import os
from flask import Flask, send_file, send_from_directory, request
from flask_cors import CORS
from .extensions import socketIO, db
from .constants.config import APP_CONFIG
from flask_jwt_extended import JWTManager
from flask import jsonify
from http import HTTPStatus
from .routes.recruitment.campaign_routes import campaign_bp
from .routes.recruitment.chat_routes import chat_bp
from .routes.recruitment.file_routes import file_bp

# Import models để đăng ký với db
from .models.recruitment import (
    RecruitmentCampaign,
    RecruitmentRequest,
    StaffingQuota,
    RecruitmentCandidate,
    RecruitmentCandidateCampaign,
    RecruitmentCandidateCV,
    RecruitmentChatSession,
    RecruitmentChatMessage,
    Company,
    Position,
    Department,
    JobTitle,
    User,
    JobTitleDescriptionApproval,
)
from sqlalchemy import text
import pymysql


def _create_database():
    """Tạo database nếu chưa tồn tại"""
    try:
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "10.0.10.87"),
            user=os.environ.get("DB_USER", "aipt_td"),
            password=os.environ.get("DB_PASSWORD", "aipt2023"),
            port=int(os.environ.get("DB_PORT", "3306")),
        )
        cursor = conn.cursor()
        db_name = os.environ.get("DB_NAME", "dbms_recruitment_db")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Database '{db_name}' đã sẵn sàng")
    except Exception as e:
        print(f"⚠️ Lỗi tạo database: {e}")


def create_app():
    # Tạo database trước
    _create_database()

    app = Flask(__name__)
    app.config.from_object(APP_CONFIG)
    app_jwt = JWTManager(app)
    CORS(app)

    # Khởi tạo database
    db.init_app(app)

    # Tạo các bảng khi app khởi động
    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return "Hello, I'm chatbot v3.6"

    @app.route("/DB/<path:filepath>")
    def serve_file(filepath):
        decoded_path = unquote(filepath)

        # Đường dẫn tuyệt đối đến thư mục src
        base_dir = os.path.abspath(
            "DB"
        )  # không dùng app.root_path nếu nó trỏ tới /app/

        # Ghép đường dẫn file
        full_path = os.path.join(base_dir, decoded_path)

        print("📂 Đường dẫn thực tế:", full_path)

        if not os.path.exists(full_path):
            return jsonify({"error": "❌ File không tồn tại", "path": full_path}), 404

        return send_file(full_path, as_attachment=False)

    # Khởi tạo socketIO với app
    socketIO.init_app(app, cors_allowed_origins="*")

    # App jwt error
    app_jwt.expired_token_loader(handle_expired_token)
    app_jwt.invalid_token_loader(handle_invalid_token)
    app_jwt.unauthorized_loader(handle_unauthorized_token)

    app.register_blueprint(campaign_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(file_bp)

    return app


def handle_expired_token(e_token, e_message):
    return (
        jsonify(
            {
                "message": "Phiên đăng nhập đã hết hạn !",
                "exp": f"{e_message['exp']}",
            }
        ),
        HTTPStatus.UNAUTHORIZED,
    )


def handle_invalid_token(e):
    return (
        jsonify({"message": "Access token không hợp lệ !", "error": f"{e}"}),
        HTTPStatus.UNAUTHORIZED,
    )


def handle_unauthorized_token(e):
    return (
        jsonify({"message": "Không có quyền truy cập !", "error": f"{e}"}),
        HTTPStatus.UNAUTHORIZED,
    )
