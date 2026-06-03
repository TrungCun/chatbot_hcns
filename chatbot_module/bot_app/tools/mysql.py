from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

from bot_app.config import settings
from bot_app.log import get_logger

logger = get_logger(__name__)

_engine: Optional[Engine] = None


def init_mysql() -> None:
    global _engine
    try:
        _engine = create_engine(
            settings.mysql_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        # Kiểm tra kết nối ngay khi khởi tạo
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Kết nối MySQL thành công tại {settings.db_host}:{settings.db_port}/{settings.db_name}")
    except SQLAlchemyError as e:
        logger.error(f"Khởi tạo MySQL thất bại: {e}")
        raise e


def close_mysql() -> None:
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Đã đóng kết nối MySQL an toàn.")


def get_mysql_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("MySQL chưa được khởi tạo! Hãy chắc chắn init_mysql() đã chạy trong lifespan.")
    return _engine
