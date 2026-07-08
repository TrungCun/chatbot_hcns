import os
from dotenv import load_dotenv

load_dotenv()

# Server config
HOST = "0.0.0.0"
PORT = 9070
MODE = "dev"  # , "app", "prod"
TIME_ZONE = os.environ.get("TIME_ZONE")

# Database config
DB_HOST = os.environ.get("DB_HOST", "10.0.10.87")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER", "aipt")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "aipt2023")
DB_NAME = os.environ.get("DB_NAME", "training")

# Nguồn CV mặc định (FK recruitment_cv_sources.id)
DEFAULT_CV_SOURCE_ID = int(os.environ.get("DEFAULT_CV_SOURCE_ID", "1"))
# Chatbot tuyển dụng — cố định 10, FE không gửi source_id
RECRUITMENT_CHAT_SOURCE_ID = 10
DEFAULT_CHAT_SOURCE_ID = RECRUITMENT_CHAT_SOURCE_ID

# License
HASH_LICENSE_KEY = os.environ.get("HASH_LICENSE_KEY")
LICENSE_EXP = os.environ.get("LICENSE_EXP")
