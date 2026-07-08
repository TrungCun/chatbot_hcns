from .config import APP_CONFIG
import jwt
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def verify_authorization(token):
    try:
        print(APP_CONFIG.SECRET_KEY)
        # Loại bỏ tiền tố "Bearer " nếu có
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        # Giải mã token
        data = jwt.decode(token, APP_CONFIG.SECRET_KEY, algorithms=["HS256"])

        if data:
            return data.get("sub")  # Trả về giá trị "sub" trong payload
        return None

    except jwt.ExpiredSignatureError:
        logger.error("Token đã hết hạn")
        return None
    except jwt.InvalidTokenError:
        logger.error("Token không hợp lệ")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi giải mã token: {str(e)}")
        return None
